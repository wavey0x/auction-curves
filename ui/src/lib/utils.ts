import { clsx, type ClassValue } from 'clsx'
import { formatDistanceToNow, format, fromUnixTime } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

/**
 * Format ethereum addresses for display
 */
export function formatAddress(address: string, length = 5): string {
  if (!address) return ''
  if (address.length <= length * 2) return address
  return `${address.slice(0, length)}..${address.slice(-length)}`
}

/**
 * Format token amounts with proper decimals
 */
export function formatTokenAmount(
  amount: string | number,
  decimals: number = 18,
  maxDecimals: number = 4
): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (!num || num === 0) return '0'
  
  const divisor = Math.pow(10, decimals)
  const formatted = num / divisor
  
  if (formatted < 0.0001) {
    return '< 0.0001'
  }
  
  if (formatted >= 1000000) {
    return `${(formatted / 1000000).toFixed(2)}M`
  }
  
  if (formatted >= 1000) {
    return `${(formatted / 1000).toFixed(2)}K`
  }
  
  return formatted.toFixed(Math.min(maxDecimals, getSignificantDecimals(formatted)))
}

/**
 * Get number of significant decimal places needed
 */
function getSignificantDecimals(num: number): number {
  if (num >= 100) return 2
  if (num >= 1) return 3
  if (num >= 0.1) return 4
  return 6
}

/**
 * Format already human-readable token amounts (from API)
 */
export function formatReadableTokenAmount(
  amount: string | number,
  maxDecimals: number = 4
): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (!num || num === 0) return '0'
  
  if (num < 0.0001) {
    return '< 0.0001'
  }
  
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(2)}M`
  }
  
  if (num >= 1000) {
    return `${(num / 1000).toFixed(2)}K`
  }
  
  return num.toFixed(Math.min(maxDecimals, getSignificantDecimals(num)))
}

/**
 * Format USD values
 */
export function formatUSD(amount: string | number): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (!num || num === 0) return '$0.00'
  
  if (num >= 1000000) {
    return `$${(num / 1000000).toFixed(2)}M`
  }
  
  if (num >= 1000) {
    return `$${(num / 1000).toFixed(2)}K`
  }
  
  return `$${num.toFixed(2)}`
}

/**
 * Format percentages
 */
export function formatPercent(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format time ago from timestamp - compact version
 */
export function formatTimeAgo(timestamp: number | string): string {
  const date = typeof timestamp === 'number' 
    ? fromUnixTime(timestamp) 
    : new Date(timestamp)
  
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)
  const diffMonths = Math.floor(diffDays / 30)
  const diffYears = Math.floor(diffDays / 365)
  
  if (diffSeconds < 60) {
    return '< 1m ago'
  } else if (diffMinutes < 60) {
    return `${diffMinutes}m ago`
  } else if (diffHours < 24) {
    return `${diffHours}h ago`
  } else if (diffDays < 7) {
    return `${diffDays}d ago`
  } else if (diffWeeks < 4) {
    return `${diffWeeks}w ago`
  } else if (diffMonths < 12) {
    return `${diffMonths}mo ago`
  } else {
    return `${diffYears}y ago`
  }
}

/**
 * Format full date
 */
export function formatDate(timestamp: number | string): string {
  const date = typeof timestamp === 'number'
    ? fromUnixTime(timestamp)
    : new Date(timestamp)
  
  return format(date, 'MMM dd, yyyy HH:mm:ss')
}

/**
 * Format duration in seconds to human readable
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  }
  
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    const remainingSeconds = seconds % 60
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }
  
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  if (hours < 24) {
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
  }
  
  const days = Math.floor(hours / 24)
  const remainingHours = hours % 24
  return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`
}

/**
 * Get chain info for transaction links
 */
export function getChainInfo(chainId: number = 1) {
  const chains: Record<number, { name: string; logo: string; explorer: string }> = {
    1: {
      name: 'Ethereum',
      logo: '🔵',
      explorer: 'https://etherscan.io'
    },
    137: {
      name: 'Polygon',
      logo: '🟣',
      explorer: 'https://polygonscan.com'
    },
    56: {
      name: 'BSC',
      logo: '🟡',
      explorer: 'https://bscscan.com'
    },
    42161: {
      name: 'Arbitrum',
      logo: '🔵',
      explorer: 'https://arbiscan.io'
    },
    10: {
      name: 'Optimism',
      logo: '🔴',
      explorer: 'https://optimistic.etherscan.io'
    },
    31337: {
      name: 'Anvil',
      logo: '⚒️',
      explorer: '#'
    }
  }
  
  return chains[chainId] || chains[1]
}

/**
 * Create transaction link
 */
export function getTxLink(txHash: string, chainId: number = 1): string {
  const chain = getChainInfo(chainId)
  if (chain.explorer === '#') return '#'
  return `${chain.explorer}/tx/${txHash}`
}

/**
 * Create address link
 */
export function getAddressLink(address: string, chainId: number = 1): string {
  const chain = getChainInfo(chainId)
  if (chain.explorer === '#') return '#'
  return `${chain.explorer}/address/${address}`
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    return false
  }
}

/**
 * Calculate auction progress percentage
 */
export function getAuctionProgress(
  kickedAt: number,
  auctionLength: number
): number {
  const now = Date.now() / 1000
  const elapsed = now - kickedAt
  return Math.min(100, Math.max(0, (elapsed / auctionLength) * 100))
}

/**
 * Get auction status based on progress
 */
export function getAuctionStatus(progress: number): 'active' | 'ending' | 'ended' {
  if (progress >= 100) return 'ended'
  if (progress >= 90) return 'ending'
  return 'active'
}

/**
 * Generate consistent colors for addresses
 */
export function getAddressColor(address: string): string {
  const colors = [
    'bg-red-500/20 text-red-400',
    'bg-blue-500/20 text-blue-400',
    'bg-green-500/20 text-green-400',
    'bg-yellow-500/20 text-yellow-400',
    'bg-purple-500/20 text-purple-400',
    'bg-pink-500/20 text-pink-400',
    'bg-indigo-500/20 text-indigo-400',
    'bg-cyan-500/20 text-cyan-400',
  ]
  
  let hash = 0
  for (let i = 0; i < address.length; i++) {
    hash = ((hash << 5) - hash + address.charCodeAt(i)) & 0xffffffff
  }
  
  return colors[Math.abs(hash) % colors.length]
}