/**
 * Chain Data Service
 * 
 * Fetches and caches chain information and icons from:
 * - chainlist.org for chain data 
 * - ethereum-lists/chains for icons
 */

export interface ChainInfo {
  chainId: number
  name: string
  shortName?: string
  networkId: number
  nativeCurrency: {
    name: string
    symbol: string
    decimals: number
  }
  rpc: string[]
  explorers?: Array<{
    name: string
    url: string
    standard: string
  }>
  icon?: string
  tvl?: number
}

export interface ChainIcon {
  url: string
  width: number
  height: number
  format: string
}

class ChainDataService {
  private chainCache: Map<number, ChainInfo> = new Map()
  private iconCache: Map<string, ChainIcon> = new Map()
  private lastUpdated: number = 0
  private readonly CACHE_DURATION = 24 * 60 * 60 * 1000 // 24 hours
  
  /**
   * Get chain info by chain ID
   */
  async getChainInfo(chainId: number): Promise<ChainInfo | null> {
    await this.ensureDataLoaded()
    return this.chainCache.get(chainId) || null
  }
  
  /**
   * Get all chains
   */
  async getAllChains(): Promise<ChainInfo[]> {
    await this.ensureDataLoaded()
    return Array.from(this.chainCache.values())
  }
  
  /**
   * Get chain icon URL by chain name or ID
   */
  getChainIconUrl(chainId: number): string | null {
    const chain = this.chainCache.get(chainId)
    if (!chain?.icon) return null
    
    // Convert IPFS URL to HTTP gateway
    if (chain.icon.startsWith('ipfs://')) {
      return `https://ipfs.io/ipfs/${chain.icon.replace('ipfs://', '')}`
    }
    
    return chain.icon
  }
  
  /**
   * Get formatted chain display info
   */
  getChainDisplay(chainId: number): {
    name: string
    shortName: string
    icon: string | null
    nativeSymbol: string
  } | null {
    const chain = this.chainCache.get(chainId)
    if (!chain) return null
    
    return {
      name: chain.name,
      shortName: chain.shortName || chain.name,
      icon: this.getChainIconUrl(chainId),
      nativeSymbol: chain.nativeCurrency.symbol
    }
  }
  
  /**
   * Get block explorer URL for a transaction
   */
  getTxExplorerUrl(chainId: number, txHash: string): string {
    const chain = this.chainCache.get(chainId)
    const explorer = chain?.explorers?.[0]
    
    if (explorer) {
      return `${explorer.url}/tx/${txHash}`
    }
    
    // Fallback explorers
    const fallbacks: Record<number, string> = {
      1: 'https://etherscan.io',
      137: 'https://polygonscan.com',
      56: 'https://bscscan.com',
      43114: 'https://snowtrace.io',
      250: 'https://ftmscan.com',
      42161: 'https://arbiscan.io',
      10: 'https://optimistic.etherscan.io',
      8453: 'https://basescan.org',
      100: 'https://gnosisscan.io',
    }
    
    const fallbackUrl = fallbacks[chainId]
    return fallbackUrl ? `${fallbackUrl}/tx/${txHash}` : '#'
  }
  
  /**
   * Check if we need to refresh the cache
   */
  private needsRefresh(): boolean {
    return Date.now() - this.lastUpdated > this.CACHE_DURATION
  }
  
  /**
   * Ensure data is loaded and fresh
   */
  private async ensureDataLoaded(): Promise<void> {
    if (this.chainCache.size === 0 || this.needsRefresh()) {
      await this.loadChainData()
    }
  }
  
  /**
   * Load chain data from chainlist.org
   */
  private async loadChainData(): Promise<void> {
    try {
      console.log('Fetching chain data from chainlist.org...')
      
      const response = await fetch('https://chainlist.org/rpcs.json')
      const chains = await response.json() as ChainInfo[]
      
      // Clear existing cache
      this.chainCache.clear()
      
      // Process and cache chain data
      for (const chain of chains) {
        // Only cache chains with valid chainId
        if (chain.chainId && chain.chainId > 0) {
          // Try to get icon for this chain
          const icon = await this.getChainIcon(chain.name, chain.shortName)
          
          this.chainCache.set(chain.chainId, {
            ...chain,
            icon: icon?.url || null
          })
        }
      }
      
      this.lastUpdated = Date.now()
      console.log(`Loaded ${this.chainCache.size} chains`)
      
    } catch (error) {
      console.error('Failed to load chain data:', error)
      
      // Load fallback data if remote fails
      this.loadFallbackChainData()
    }
  }
  
  /**
   * Get chain icon from ethereum-lists/chains repo
   */
  private async getChainIcon(name: string, shortName?: string): Promise<ChainIcon | null> {
    const possibleNames = [
      name.toLowerCase().replace(/\s+/g, ''),
      shortName?.toLowerCase(),
      name.toLowerCase().replace(/\s+/g, '-'),
      name.toLowerCase().replace(/\s+/g, '_')
    ].filter(Boolean)
    
    for (const iconName of possibleNames) {
      try {
        const url = `https://raw.githubusercontent.com/ethereum-lists/chains/master/_data/icons/${iconName}.json`
        const response = await fetch(url)
        
        if (response.ok) {
          const iconData = await response.json()
          
          if (Array.isArray(iconData) && iconData.length > 0) {
            const icon = iconData[0]
            return {
              url: icon.url,
              width: icon.width,
              height: icon.height,
              format: icon.format
            }
          }
        }
      } catch (error) {
        // Continue trying other names
      }
    }
    
    return null
  }
  
  /**
   * Load fallback chain data for common networks
   */
  private loadFallbackChainData(): void {
    const fallbackChains: ChainInfo[] = [
      {
        chainId: 1,
        name: 'Ethereum Mainnet',
        shortName: 'eth',
        networkId: 1,
        nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        rpc: ['https://eth.llamarpc.com'],
        explorers: [{ name: 'Etherscan', url: 'https://etherscan.io', standard: 'EIP3091' }],
        icon: 'ipfs://QmdwQDr6vmBtXmK2TmknkEuZNoaDqTasFdZdu3DRw8b2wt'
      },
      {
        chainId: 137,
        name: 'Polygon Mainnet',
        shortName: 'matic',
        networkId: 137,
        nativeCurrency: { name: 'MATIC', symbol: 'MATIC', decimals: 18 },
        rpc: ['https://polygon.llamarpc.com'],
        explorers: [{ name: 'PolygonScan', url: 'https://polygonscan.com', standard: 'EIP3091' }],
      },
      {
        chainId: 31337,
        name: 'Anvil Local',
        shortName: 'anvil',
        networkId: 31337,
        nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        rpc: ['http://127.0.0.1:8545'],
        explorers: [],
        icon: 'ipfs://QmdwQDr6vmBtXmK2TmknkEuZNoaDqTasFdZdu3DRw8b2wt' // Use ETH icon
      },
      {
        chainId: 56,
        name: 'BNB Smart Chain',
        shortName: 'bnb',
        networkId: 56,
        nativeCurrency: { name: 'BNB', symbol: 'BNB', decimals: 18 },
        rpc: ['https://binance.llamarpc.com'],
        explorers: [{ name: 'BscScan', url: 'https://bscscan.com', standard: 'EIP3091' }],
      },
      {
        chainId: 42161,
        name: 'Arbitrum One',
        shortName: 'arb1',
        networkId: 42161,
        nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        rpc: ['https://arbitrum.llamarpc.com'],
        explorers: [{ name: 'Arbiscan', url: 'https://arbiscan.io', standard: 'EIP3091' }],
      },
    ]
    
    for (const chain of fallbackChains) {
      this.chainCache.set(chain.chainId, chain)
    }
    
    console.log('Loaded fallback chain data')
  }
  
  /**
   * Force refresh the cache
   */
  async refreshCache(): Promise<void> {
    this.lastUpdated = 0
    await this.loadChainData()
  }
}

// Export singleton instance
export const chainDataService = new ChainDataService()

// Convenience functions
export const getChainInfo = (chainId: number) => chainDataService.getChainInfo(chainId)
export const getChainDisplay = (chainId: number) => chainDataService.getChainDisplay(chainId)
export const getTxExplorerUrl = (chainId: number, txHash: string) => chainDataService.getTxExplorerUrl(chainId, txHash)
export const getChainIconUrl = (chainId: number) => chainDataService.getChainIconUrl(chainId)