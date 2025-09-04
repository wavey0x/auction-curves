export type NotificationType = 'kick' | 'take' | 'deploy'

export interface NotificationContent {
  // Common fields
  chainId: number
  chainName: string
  auctionAddress: string
  txHash?: string
  
  // Kick-specific fields
  roundId?: number
  fromTokenSymbol?: string
  wantTokenSymbol?: string
  initialAvailable?: string
  kicker?: string
  
  // Take-specific fields
  taker?: string
  amountTaken?: string
  amountPaid?: string
  
  // Deploy-specific fields
  version?: string
  wantToken?: string
  startingPrice?: string
  decayRate?: string
  governance?: string
}

export interface Notification {
  id: string // uniq field from Redis
  type: NotificationType
  timestamp: number
  dismissAt: number // timestamp for auto-dismiss
  content: NotificationContent
}

export interface NotificationContextType {
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'dismissAt'>) => void
  removeNotification: (id: string) => void
  clearAllNotifications: () => void
}

export interface RedisStreamEvent {
  type: string
  chain_id: string
  block_number: string
  tx_hash: string
  log_index: string
  auction_address: string
  timestamp: string
  uniq: string
  ver: string
  payload_json: string
  round_id?: string
  from_token?: string
  want_token?: string
}