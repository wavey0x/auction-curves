/**
 * RPC Service using viem for blockchain interactions
 * Provides clients for each chain using public RPC endpoints
 */

import { createPublicClient, http, type PublicClient, type Chain } from 'viem'
import { mainnet, polygon, arbitrum, optimism, base, bsc } from 'viem/chains'
import { chainDataService } from './chainData'

// Define local anvil chain
const anvil: Chain = {
  id: 31337,
  name: 'Anvil Local',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: {
    default: { http: ['http://127.0.0.1:8545'] },
    public: { http: ['http://127.0.0.1:8545'] }
  },
  blockExplorers: {
    default: { name: 'Local', url: '' }
  }
}

// Map of chain IDs to viem chain objects
const chainMap: Record<number, Chain> = {
  1: mainnet,
  137: polygon,
  42161: arbitrum,
  10: optimism,
  8453: base,
  56: bsc,
  31337: anvil
}

class RPCService {
  private clients: Map<number, PublicClient> = new Map()
  private customRpcEnabled = false
  private customRpcUrl: string | null = null
  private onCustomRPCError: ((error: unknown) => void) | null = null
  
  /**
   * Get or create a public client for a specific chain
   */
  async getClient(chainId: number): Promise<PublicClient | null> {
    // Check if we already have a client for this chain
    if (this.clients.has(chainId)) {
      return this.clients.get(chainId)!
    }
    
    try {
      const client = await this.createClient(chainId)
      if (client) {
        this.clients.set(chainId, client)
      }
      return client
    } catch (error) {
      console.error(`Failed to create RPC client for chain ${chainId}:`, error)
      return null
    }
  }
  
  /**
   * Extract clean URL without credentials for chain metadata
   */
  private getCleanUrl(url: string): string {
    try {
      const urlObj = new URL(url)
      return `${urlObj.protocol}//${urlObj.host}${urlObj.pathname}${urlObj.search}${urlObj.hash}`
    } catch (error) {
      return url // Return original if parsing fails
    }
  }

  /**
   * Extract credentials from URL and create proper transport config
   */
  private createHttpTransport(url: string) {
    try {
      const urlObj = new URL(url)
      
      // Check if URL has embedded credentials
      if (urlObj.username || urlObj.password) {
        // Extract credentials
        const auth = urlObj.username && urlObj.password ? 
          btoa(`${urlObj.username}:${urlObj.password}`) : null
        
        // Clean URL without credentials
        const cleanUrl = `${urlObj.protocol}//${urlObj.host}${urlObj.pathname}${urlObj.search}${urlObj.hash}`
        
        // Create transport with proper auth headers
        return http(cleanUrl, {
          fetchOptions: auth ? {
            headers: {
              'Authorization': `Basic ${auth}`
            }
          } : undefined
        })
      } else {
        // No credentials, use URL as-is
        return http(url)
      }
    } catch (error) {
      console.error('Invalid RPC URL:', url, error)
      return http(url) // Fallback to original URL
    }
  }

  /**
   * Create a new viem client for a chain
   */
  private async createClient(chainId: number): Promise<PublicClient | null> {
    // If a custom RPC is enabled, prefer it for transport
    const useCustom = this.customRpcEnabled && this.customRpcUrl

    // First try to get chain from viem's built-in chains
    const viemChain = chainMap[chainId]
    if (viemChain) {
      return createPublicClient({
        chain: viemChain,
        transport: useCustom ? this.createHttpTransport(this.customRpcUrl!) : http()
      })
    }
    
    // Fallback: get RPC URLs from chainData service
    const chainInfo = await chainDataService.getChainInfo(chainId)
    if (!chainInfo?.rpc?.length) {
      console.warn(`No RPC URLs found for chain ${chainId}`)
      return null
    }
    
    // Use first available RPC URL
    const rpcUrl = chainInfo.rpc[0]
    if (!rpcUrl) {
      return null
    }
    
    // Create custom chain definition (URLs for chain metadata only, transport handles auth)
    const cleanUrl = useCustom ? this.getCleanUrl(this.customRpcUrl!) : rpcUrl
    const customChain: Chain = {
      id: chainId,
      name: chainInfo.name,
      nativeCurrency: chainInfo.nativeCurrency,
      rpcUrls: {
        default: { http: [cleanUrl] },
        public: { http: [cleanUrl] }
      },
      blockExplorers: chainInfo.explorers?.length ? {
        default: {
          name: chainInfo.explorers[0].name,
          url: chainInfo.explorers[0].url
        }
      } : undefined
    }
    
    return createPublicClient({
      chain: customChain,
      transport: useCustom ? this.createHttpTransport(this.customRpcUrl!) : http(rpcUrl)
    })
  }
  
  /**
   * Test if a client is working
   */
  async testClient(chainId: number): Promise<boolean> {
    try {
      const client = await this.getClient(chainId)
      if (!client) return false
      
      // Try to get the latest block number
      await client.getBlockNumber()
      return true
    } catch (error) {
      console.error(`Client test failed for chain ${chainId}:`, error)
      return false
    }
  }
  
  /**
   * Clear all clients (useful for testing or config changes)
   */
  clearClients(): void {
    this.clients.clear()
  }
  
  /**
   * Get list of supported chain IDs
   */
  getSupportedChains(): number[] {
    return Object.keys(chainMap).map(Number)
  }

  // --- Custom RPC controls ---
  setCustomRPCConfig(enabled: boolean, url?: string | null) {
    const normalizedUrl = (url ?? '').trim() || null
    const changed = this.customRpcEnabled !== enabled || this.customRpcUrl !== normalizedUrl
    this.customRpcEnabled = enabled
    this.customRpcUrl = normalizedUrl
    if (changed) {
      // Clear existing clients so new transports are picked up
      this.clearClients()
    }
  }

  isCustomRPCEnabled() {
    return !!this.customRpcEnabled && !!this.customRpcUrl
  }

  getCustomRPCUrl() {
    return this.customRpcUrl
  }

  setCustomRPCErrorHandler(handler: ((error: unknown) => void) | null) {
    this.onCustomRPCError = handler
  }

  reportCustomRPCError(error: unknown) {
    if (this.customRpcEnabled && this.onCustomRPCError) {
      try { this.onCustomRPCError(error) } catch {}
    }
  }
}

// Export singleton instance
export const rpcService = new RPCService()

// Convenience functions
export const getRPCClient = (chainId: number) => rpcService.getClient(chainId)
export const testRPCClient = (chainId: number) => rpcService.testClient(chainId)
