import { RedisStreamEvent, Notification, NotificationContent } from '../types/notification'

export class EventStreamService {
  private eventSource: EventSource | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: ((notification: Omit<Notification, 'dismissAt'>) => void)[] = []
  private isConnected = false
  private fiveMinutesMs = 5 * 60 * 1000

  constructor() {
    this.connect = this.connect.bind(this)
    this.disconnect = this.disconnect.bind(this)
  }

  private getSeenEvents(): Record<string, number> {
    try {
      const stored = localStorage.getItem('seenNotifications')
      return stored ? JSON.parse(stored) : {}
    } catch (error) {
      console.warn('Failed to load seen notifications:', error)
      return {}
    }
  }

  private saveSeenEvents(seenEvents: Record<string, number>) {
    try {
      // Auto-cleanup: remove events older than 5 minutes
      const now = Date.now()
      const cutoffTime = now - this.fiveMinutesMs
      const cleanedEvents: Record<string, number> = {}
      
      for (const [eventId, timestamp] of Object.entries(seenEvents)) {
        if (timestamp > cutoffTime) {
          cleanedEvents[eventId] = timestamp
        }
      }
      
      localStorage.setItem('seenNotifications', JSON.stringify(cleanedEvents))
    } catch (error) {
      console.warn('Failed to save seen notifications:', error)
    }
  }

  private getMostRecentEventWithin5Minutes(): string | null {
    const seenEvents = this.getSeenEvents()
    const now = Date.now()
    const fiveMinutesAgo = now - this.fiveMinutesMs
    
    let mostRecentId: string | null = null
    let mostRecentTimestamp = 0
    
    for (const [eventId, timestamp] of Object.entries(seenEvents)) {
      if (timestamp > fiveMinutesAgo && timestamp > mostRecentTimestamp) {
        mostRecentTimestamp = timestamp
        mostRecentId = eventId
      }
    }
    
    return mostRecentId
  }

  addListener(callback: (notification: Omit<Notification, 'dismissAt'>) => void) {
    this.listeners.push(callback)
    return () => {
      this.listeners = this.listeners.filter(listener => listener !== callback)
    }
  }

  connect() {
    if (this.eventSource?.readyState === EventSource.OPEN) {
      return
    }

    // Check for most recent seen event within 5 minutes
    const mostRecentId = this.getMostRecentEventWithin5Minutes()
    const fromParam = mostRecentId ? `?from=${encodeURIComponent(mostRecentId)}` : ''
    
    this.eventSource = new EventSource(`/api/events/stream${fromParam}`)

    this.eventSource.onopen = () => {
      this.isConnected = true
      this.reconnectAttempts = 0
    }

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Handle system messages (like "connected", heartbeat)
        if (data.type === 'connected') {
          console.log('📡 Event stream ready')
          return
        }
        if (data.type === 'heartbeat') {
          return // Silent heartbeat
        }
        
        // Handle Redis stream events
        const notification = this.transformEventToNotification(data as RedisStreamEvent)
        if (notification) {
          // Simple deduplication check
          const seenEvents = this.getSeenEvents()
          
          if (!seenEvents[notification.id]) {
            // New notification - add to seen list and show
            seenEvents[notification.id] = Date.now()
            this.saveSeenEvents(seenEvents)
            this.listeners.forEach(listener => listener(notification))
          }
          // If already seen, silently ignore
        }
      } catch (error) {
        console.error('Failed to parse event stream message:', error, 'Raw data:', event.data)
      }
    }

    this.eventSource.onerror = (event) => {
      console.log('📡 SSE error event:', event)
      this.isConnected = false
      
      // Close the problematic connection immediately
      if (this.eventSource) {
        this.eventSource.close()
        this.eventSource = null
      }
      
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000) // Cap at 30s
        console.log(`📡 Event stream error, reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
        
        setTimeout(() => {
          this.connect()
        }, delay)
      } else {
        console.error('📡 Event stream failed after max reconnection attempts')
      }
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    this.isConnected = false
  }

  getConnectionStatus() {
    return this.isConnected
  }

  private transformEventToNotification(event: RedisStreamEvent): Omit<Notification, 'dismissAt'> | null {
    try {
      // Handle payload_json - should now be an object after backend processing
      let payload = {}
      if (event.payload_json) {
        if (typeof event.payload_json === 'object') {
          payload = event.payload_json
        } else if (typeof event.payload_json === 'string' && event.payload_json !== 'undefined') {
          try {
            payload = JSON.parse(event.payload_json)
          } catch (parseError) {
            console.warn('Failed to parse event payload_json:', event.payload_json)
            payload = {}
          }
        }
      }
      
      const chainId = parseInt(event.chain_id)
      const type = event.type as 'kick' | 'take' | 'deploy'

      // Get chain name
      const chainName = this.getChainName(chainId)

      const baseContent: NotificationContent = {
        chainId,
        chainName,
        auctionAddress: event.auction_address,
        txHash: event.tx_hash
      }

      let content: NotificationContent

      switch (type) {
        case 'kick':
          content = {
            ...baseContent,
            roundId: event.round_id ? parseInt(event.round_id) : undefined,
            fromTokenSymbol: this.getTokenSymbol(event.from_token, chainId),
            wantTokenSymbol: this.getTokenSymbol(event.want_token, chainId),
            initialAvailable: payload.initial_available,
            kicker: payload.kicker
          }
          break

        case 'take':
          content = {
            ...baseContent,
            roundId: event.round_id ? parseInt(event.round_id) : undefined,
            taker: payload.taker,
            amountTaken: payload.amount_taken,
            amountPaid: payload.amount_paid,
            fromTokenSymbol: this.getTokenSymbol(event.from_token, chainId),
            wantTokenSymbol: this.getTokenSymbol(event.want_token, chainId)
          }
          break

        case 'deploy':
          content = {
            ...baseContent,
            version: payload.version,
            wantTokenSymbol: this.getTokenSymbol(event.want_token, chainId),
            startingPrice: payload.starting_price,
            decayRate: payload.decay_rate,
            governance: payload.governance
          }
          break

        default:
          return null
      }

      return {
        id: event.id || event.uniq, // Use event.id from fire_events.py, fallback to uniq for indexer events
        type,
        timestamp: Date.now(), // Use current time since fire_events doesn't provide timestamp
        content
      } as Omit<Notification, 'dismissAt'>
    } catch (error) {
      console.error('Failed to transform event to notification:', error)
      return null
    }
  }

  private getChainName(chainId: number): string {
    const chains: Record<number, string> = {
      1: 'Ethereum',
      137: 'Polygon',
      42161: 'Arbitrum',
      10: 'Optimism',
      8453: 'Base',
      31337: 'Local'
    }
    return chains[chainId] || `Chain ${chainId}`
  }

  private getTokenSymbol(tokenAddress: string | undefined, _chainId: number): string {
    // For now, return a generic token symbol
    // In a real implementation, you might want to fetch token metadata
    // or use a token registry/cache
    if (!tokenAddress) return 'TOKEN'
    
    // Known token addresses (you could expand this or fetch from API)
    const knownTokens: Record<string, string> = {
      // Ethereum mainnet
      '0xa0b86991c31cc0ea63c7e0bfec4f8e5c0e2e0c0e2': 'USDC', // USDC
      '0xdac17f958d2ee523a2206206994597c13d831ec7': 'USDT', // USDT
      '0x6b175474e89094c44da98b954eedeac495271d0f': 'DAI',  // DAI
      '0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e': 'YFI',  // YFI
    }

    return knownTokens[tokenAddress.toLowerCase()] || 'TOKEN'
  }
}

// Singleton instance
export const eventStreamService = new EventStreamService()