import type { 
  AuctionListItem,
  AuctionDetails,
  AuctionRoundHistory,
  PriceHistory,
  AuctionTake,
  Token,
  SystemStats,
  PaginatedTakesResponse,
} from '../types/auction'
import type { 
  TakerListResponse, 
  TakerDetail, 
  TakerTakesResponse,
  TokenPairsResponse 
} from '../types/taker'
import type { TakeDetail } from '../types/take'

const BASE_URL = '/api'

class APIClient {
  async getStatus(): Promise<any> {
    const response = await fetch(`/api/status`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    if (!response.ok) {
      throw new Error(`Failed to fetch status: ${response.statusText}`)
    }
    return response.json()
  }
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
    
    // Add timestamp to prevent caching
    searchParams.append('_t', Date.now().toString())
    const url = `/auctions?${searchParams.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auctions: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getAuction(address: string, chainId: number): Promise<AuctionDetails> {
    const response = await fetch(`${BASE_URL}/auctions/${chainId}/${address}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getAuctionRounds(
    auctionAddress: string, 
    chainId: number,
    fromToken?: string, 
    limit: number = 50
  ): Promise<AuctionRoundHistory> {
    let url = `/auctions/${chainId}/${auctionAddress}/rounds?limit=${limit}`
    if (fromToken) {
      url += `&from_token=${fromToken}`
    }
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction rounds: ${response.statusText}`)
    }
    
    return response.json()
  }

  // Add a specific method to get a single round by ID
  async getAuctionRound(
    auctionAddress: string,
    chainId: number, 
    roundId: number
  ): Promise<any> {
    const url = `/auctions/${chainId}/${auctionAddress}/rounds?round_id=${roundId}&limit=1`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction round: ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.rounds?.[0] || null
  }

  async getAuctionTakes(
    auctionAddress: string,
    chainId: number,
    roundId?: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<PaginatedTakesResponse> {
    let url = `/auctions/${chainId}/${auctionAddress}/takes?limit=${limit}&offset=${offset}`
    if (roundId) url += `&round_id=${roundId}`
    
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch auction takes: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getPriceHistory(
    auctionAddress: string,
    chainId: number,
    fromToken: string,
    hours: number = 24
  ): Promise<PriceHistory> {
    const url = `/auctions/${chainId}/${auctionAddress}/price-history?from_token=${fromToken}&hours=${hours}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
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

  // Recent takes across all auctions
  async getRecentTakes(limit: number = 50, chainId?: number): Promise<AuctionTake[]> {
    const searchParams = new URLSearchParams()
    searchParams.append('limit', String(limit))
    if (chainId !== undefined) searchParams.append('chain_id', String(chainId))
    const url = `/activity/takes?${searchParams.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    if (!response.ok) {
      throw new Error(`Failed to fetch recent takes: ${response.statusText}`)
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

  // Taker endpoints
  async getTakers(params?: {
    sort_by?: string
    page?: number
    limit?: number
    chain_id?: number
  }): Promise<TakerListResponse> {
    const searchParams = new URLSearchParams()
    
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.chain_id) searchParams.append('chain_id', params.chain_id.toString())
    
    // Add timestamp to prevent caching
    searchParams.append('_t', Date.now().toString())
    const url = `/takers?${searchParams.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch takers: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getTakerDetails(address: string): Promise<TakerDetail> {
    const response = await fetch(`${BASE_URL}/takers/${address}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch taker details: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getTakerTakes(address: string, params?: {
    page?: number
    limit?: number
    chain_id?: number
  }): Promise<TakerTakesResponse> {
    const searchParams = new URLSearchParams()
    
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.chain_id) searchParams.append('chain_id', params.chain_id.toString())
    
    // Add timestamp to prevent caching
    searchParams.append('_t', Date.now().toString())
    const url = `/takers/${address}/takes?${searchParams.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch taker takes: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getTakerTokenPairs(address: string, params?: {
    page?: number
    limit?: number
  }): Promise<TokenPairsResponse> {
    // Add timestamp to prevent caching
    const searchParams = new URLSearchParams()
    
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    
    searchParams.append('_t', Date.now().toString())
    const url = `/takers/${address}/token-pairs?${searchParams.toString()}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch taker token pairs: ${response.statusText}`)
    }
    
    return response.json()
  }

  async getTakeDetails(chainId: number, auctionAddress: string, roundId: number, takeSeq: number): Promise<TakeDetail> {
    const url = `/takes/${chainId}/${auctionAddress}/${roundId}/${takeSeq}`
    const response = await fetch(`${BASE_URL}${url}`, {
      cache: 'no-cache',
      headers: { 'Cache-Control': 'no-cache' }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch take details: ${response.statusText}`)
    }
    
    return response.json()
  }

}

export const apiClient = new APIClient()
