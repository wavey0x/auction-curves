export interface Token {
  address: string;
  symbol: string;
  name: string;
  decimals: number;
}

export interface AuctionParameters {
  price_update_interval: number;
  step_decay: string;
  auction_length: number;
  starting_price: string;
  fixed_starting_price?: string;
}

export interface AuctionRoundInfo {
  round_id: number;
  kicked_at: string;
  initial_available: string;
  is_active: boolean;
  current_price?: string;
  available_amount?: string;
  time_remaining?: number;
  seconds_elapsed: number;
  total_sales: number;
  progress_percentage?: number;
}

export interface AuctionSale {
  sale_id: string;
  auction: string;
  chain_id: number;
  round_id: number;
  sale_seq: number;
  taker: string;
  amount_taken: string;
  amount_paid: string;
  price: string;
  timestamp: string;
  tx_hash: string;
  block_number: number;
}

export interface AuctionActivity {
  total_participants: number;
  total_volume: string;
  total_rounds: number;
  total_sales: number;
  recent_sales: AuctionSale[];
}

export interface AuctionListItem {
  address: string;
  chain_id: number;
  from_tokens: Token[];
  want_token: Token;
  current_round?: AuctionRoundInfo;
  last_kicked?: string;
  decay_rate_percent: number;
  update_interval_minutes: number;
}

export interface AuctionDetails {
  address: string;
  chain_id: number;
  factory_address?: string;
  deployer: string;
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
  total_sales: number;
  total_participants: number;
}
