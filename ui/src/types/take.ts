export interface PriceQuote {
  source: string
  token_address: string
  token_symbol?: string
  price_usd: number
  block_number: number
  timestamp: number
  block_distance: number
  time_distance: number
}

export interface PnLAnalysis {
  base_pnl: number
  best_case_pnl: number
  worst_case_pnl: number
  average_pnl: number
  price_variance_percent: number
  take_value_usd: number
}

export interface TakeDetail {
  // Core take data
  take_id: string
  auction_address: string
  chain_id: number
  round_id: number
  take_seq: number
  taker: string
  
  // Token exchange details
  from_token: string
  to_token: string
  from_token_symbol?: string
  to_token_symbol?: string
  amount_taken: string
  amount_paid: string
  price: string
  
  // Transaction details
  tx_hash: string
  block_number: number
  timestamp: string
  
  // Gas costs
  gas_price?: number
  base_fee?: number
  priority_fee?: number
  gas_used?: number
  transaction_fee_eth?: number
  transaction_fee_usd?: number
  
  // Price analysis
  price_quotes: PriceQuote[]
  pnl_analysis: PnLAnalysis
  
  // Auction context
  auction_decay_rate?: number
  auction_update_interval?: number
  round_total_takes?: number
  round_available_before?: string
  round_available_after?: string
}