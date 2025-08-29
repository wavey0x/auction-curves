import type { 
  AuctionListItem,
  AuctionDetails,
  AuctionRoundHistory,
  PriceHistory,
  AuctionSale,
  Token,
  SystemStats,
} from '../types/auction'

const BASE_URL = '/api'

class APIClient {
  // New Auction endpoints
  async getAuctions(params?: {
    status?: 'all' | 'active' | 'completed'
    from_token?: string
    want_token?: string
    page?: number
    limit?: number
  }): Promise<{
    auctions: AuctionListItem[]
    total: number
    page: number
    per_page: number
    has_next: boolean
  }> {
    const searchParams = new URLSearchParams()
    
    if (params?.status) searchParams.append('status', params.status)
    if (params?.from_token) searchParams.append('from_token', params.from_token)
    if (params?.want_token) searchParams.append('want_token', params.want_token)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    
    const url = `/auctions?${searchParams.toString()}`
    const response = await fetch(`${BASE_URL}${url}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auctions: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getAuction(address: string): Promise<AuctionDetails> {
    const response = await fetch(`${BASE_URL}/auctions/${address}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getAuctionRounds(
    auctionAddress: string, 
    fromToken: string, 
    limit: number = 50
  ): Promise<AuctionRoundHistory> {
    const url = `/auctions/${auctionAddress}/rounds?from_token=${fromToken}&limit=${limit}`
    const response = await fetch(`${BASE_URL}${url}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction rounds: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getAuctionSales(
    auctionAddress: string,
    roundId?: number,
    limit: number = 50
  ): Promise<AuctionSale[]> {
    let url = `/auctions/${auctionAddress}/sales?limit=${limit}`
    if (roundId) url += `&round_id=${roundId}`
    
    const response = await fetch(`${BASE_URL}${url}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction sales: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getPriceHistory(
    auctionAddress: string,
    fromToken: string,
    hours: number = 24
  ): Promise<PriceHistory> {
    const url = `/auctions/${auctionAddress}/price-history?from_token=${fromToken}&hours=${hours}`
    const response = await fetch(`${BASE_URL}${url}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch price history: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getTokens(): Promise<{ tokens: Token[], count: number }> {
    const response = await fetch(`${BASE_URL}/tokens`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch tokens: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Chain endpoints
  async getChains(): Promise<{ chains: Record<number, any>, count: number }> {
    const response = await fetch(`${BASE_URL}/chains`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch chains: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getChain(chainId: number): Promise<any> {
    const response = await fetch(`${BASE_URL}/chains/${chainId}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch chain ${chainId}: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getSystemStats(): Promise<SystemStats> {
    const response = await fetch(`${BASE_URL}/system/stats`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch system stats: ${response.statusText}`)
    }
    
    return response.json()
  }

}

export const apiClient = new APIClient()