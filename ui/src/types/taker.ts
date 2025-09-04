export interface TakerSummary {
  taker: string
  total_takes: number
  unique_auctions: number
  unique_chains: number
  total_volume_usd: number | null
  avg_take_size_usd: number | null
  last_take: string | null
  first_take: string | null
  rank_by_takes: number
  rank_by_volume: number | null
  active_chains: number[]
}

export interface TakerDetail {
  taker: string
  total_takes: number
  unique_auctions: number
  unique_chains: number
  total_volume_usd: number | null
  avg_take_size_usd: number | null
  last_take: string | null
  first_take: string | null
  rank_by_takes: number
  rank_by_volume: number | null
  active_chains: number[]
  auction_breakdown: AuctionBreakdown[]
}

export interface AuctionBreakdown {
  auction_address: string
  chain_id: number
  takes_count: number
  volume_usd: number | null
  last_take: string | null
  first_take: string | null
}

export interface TakerListResponse {
  takers: TakerSummary[]
  total: number
  page: number
  per_page: number
  has_next: boolean
}

export interface TakerTake {
  take_id: string
  chain_id: number
  block_number: number
  auction_address: string
  round_id: number
  sequence: number
  taker: string
  timestamp: string
  tx_hash: string
  available_before: string
  sold: string
  price: string
  price_usd: number | null
}

export interface TakerTakesResponse {
  takes: TakerTake[]
  total_count: number
  page: number
  limit: number
  total_pages: number
}

export interface TokenPair {
  from_token: string
  to_token: string
  takes_count: number
  volume_usd: number | null
  last_take_at: string | null
  first_take_at: string | null
  unique_auctions: number
  unique_chains: number
  from_token_symbol: string | null
  from_token_name: string | null
  from_token_decimals: number | null
  to_token_symbol: string | null
  to_token_name: string | null
  to_token_decimals: number | null
  active_chains: number[]
}

export interface TokenPairsResponse {
  token_pairs: TokenPair[]
}