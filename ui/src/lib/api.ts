import axios from 'axios'
import type {
  AuctionSummary,
  AuctionDetails,
  ActivityEvent,
  Token,
  SystemStats,
  PriceData,
} from '../types/auction'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Response types for API
interface AuctionResponse {
  auctions: AuctionSummary[]
  count: number
}

interface ActivityResponse {
  events: ActivityEvent[]
  count: number
  has_more: boolean
}

interface TokenResponse {
  tokens: Token[]
  count: number
}

interface PriceResponse {
  prices: PriceData[]
  count: number
}

// API functions
export const apiClient = {
  // System overview
  async getSystemStats(): Promise<SystemStats> {
    const response = await api.get('/analytics/overview')
    return response.data.system_stats
  },

  // Auctions
  async getAuctions(): Promise<AuctionSummary[]> {
    const response = await api.get<AuctionResponse>('/auctions')
    return response.data.auctions
  },

  async getAuction(address: string): Promise<AuctionDetails> {
    const response = await api.get<AuctionDetails>(`/auctions/${address}`)
    return response.data
  },

  // Activity events
  async getRecentActivity(limit = 50): Promise<ActivityEvent[]> {
    const response = await api.get<ActivityResponse>('/activity/recent', {
      params: { limit }
    })
    return response.data.events
  },

  async getKicks(limit = 50): Promise<ActivityEvent[]> {
    const response = await api.get<ActivityResponse>('/activity/kicks', {
      params: { limit }
    })
    return response.data.events
  },

  async getTakes(limit = 50): Promise<ActivityEvent[]> {
    const response = await api.get<ActivityResponse>('/activity/takes', {
      params: { limit }
    })
    return response.data.events
  },

  async getAuctionActivity(
    address: string,
    limit = 50
  ): Promise<ActivityEvent[]> {
    const response = await api.get<ActivityResponse>(
      `/activity/auction/${address}`,
      { params: { limit } }
    )
    return response.data.events
  },

  // Tokens
  async getTokens(): Promise<Token[]> {
    const response = await api.get<TokenResponse>('/tokens')
    return response.data.tokens
  },

  async getToken(address: string): Promise<Token> {
    const response = await api.get<Token>(`/tokens/${address}`)
    return response.data
  },

  // Price data
  async getPriceHistory(
    auctionAddress: string,
    fromToken: string,
    hours = 24
  ): Promise<PriceData[]> {
    const response = await api.get<PriceResponse>(
      `/prices/history/${auctionAddress}`,
      {
        params: {
          from_token: fromToken,
          hours
        }
      }
    )
    return response.data.prices
  },

  async getCurrentPrices(): Promise<PriceData[]> {
    const response = await api.get<PriceResponse>('/prices/current')
    return response.data.prices
  },
}

// WebSocket connection for real-time updates
export class AuctionWebSocket {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(
    private auctionAddress: string,
    private onMessage: (data: any) => void,
    private onError?: (error: Event) => void
  ) {}

  connect() {
    try {
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${
        window.location.host
      }/ws/auction/${this.auctionAddress}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected to auction:', this.auctionAddress)
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.handleReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        if (this.onError) {
          this.onError(error)
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Reconnecting... attempt ${this.reconnectAttempts}`)
        this.connect()
      }, this.reconnectDelay * this.reconnectAttempts)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export default apiClient