export interface Token {
  address: string;
  symbol: string;
  name: string;
  decimals: number;
  chain_id: number;
}

export interface AuctionParameters {
  price_update_interval: number;
  step_decay?: string;
  step_decay_rate?: string;
  decay_rate?: number;
  auction_length: number;
  starting_price: string;
  fixed_starting_price?: string;
}

export interface AuctionRoundInfo {
  round_id: number;
  kicked_at: string;
  round_start?: number;  // Unix timestamp
  round_end?: number;    // Unix timestamp
  initial_available: string;
  is_active: boolean;
  current_price?: string;
  available_amount?: string;
  time_remaining?: number;
  seconds_elapsed: number;
  total_takes: number;
  progress_percentage?: number;
}

export interface AuctionTake {
  take_id: string;
  auction: string;
  chain_id: number;
  round_id: number;
  take_seq: number;
  taker: string;
  amount_taken: string;
  amount_paid: string;
  price: string;
  timestamp: string;
  tx_hash: string;
  block_number: number;
  // Token information
  from_token?: string;
  to_token?: string;
  from_token_symbol?: string;
  from_token_name?: string;
  from_token_decimals?: number;
  to_token_symbol?: string;
  to_token_name?: string;
  to_token_decimals?: number;
  // USD price information
  from_token_price_usd?: string;
  want_token_price_usd?: string;
  amount_taken_usd?: string;
  amount_paid_usd?: string;
  price_differential_usd?: string;
  price_differential_percent?: number;
}

export interface AuctionActivity {
  total_participants: number;
  total_volume: string;
  total_rounds: number;
  total_takes: number;
  recent_takes: AuctionTake[];
}

export interface AuctionListItem {
  address: string;
  chain_id: number;
  from_tokens: Token[];
  want_token: Token;
  current_round?: AuctionRoundInfo;
  last_kicked?: string;
  decay_rate: number;
  update_interval: number;
}

export interface AuctionDetails {
  address: string;
  chain_id: number;
  factory_address?: string;
  deployer: string;
  governance?: string;
  from_tokens: Token[];
  want_token: Token;
  parameters: AuctionParameters;
  current_round?: AuctionRoundInfo;
  activity: AuctionActivity;
  deployed_at: string;
  last_kicked?: string;
}

export interface AuctionRoundHistory {
  auction: string;
  from_token: string;
  rounds: AuctionRoundInfo[];
  total_rounds: number;
}

export interface PriceHistoryPoint {
  timestamp: string;
  price: string;
  available_amount: string;
  seconds_from_kick: number;
  round_id: number;
}

export interface PriceHistory {
  auction: string;
  from_token: string;
  points: PriceHistoryPoint[];
  duration_hours: number;
}

export interface SystemStats {
  total_auctions: number;
  active_auctions: number;
  unique_tokens: number;
  total_rounds: number;
  total_takes: number;
  total_participants: number;
  total_volume_usd?: number;
}

export interface PaginatedTakesResponse {
  takes: AuctionTake[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
