import React from 'react'
import InternalLink from './InternalLink'
import { Activity } from 'lucide-react'
import { cn } from '../lib/utils'

interface TakeLinkProps {
  chainId: number
  auctionAddress: string
  roundId: number
  takeSeq: number
  children?: React.ReactNode
  className?: string
  variant?: 'default' | 'icon' | 'minimal'
  size?: 'sm' | 'md' | 'lg'
}

const TakeLink: React.FC<TakeLinkProps> = ({
  chainId,
  auctionAddress,
  roundId,
  takeSeq,
  children,
  className,
  variant = 'default',
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm', 
    lg: 'text-base'
  }

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  }

  const takeId = `${auctionAddress}-${roundId}-${takeSeq}`
  
  if (variant === 'icon') {
    return (
      <InternalLink 
        to={`/take/${chainId}/${auctionAddress}/${roundId}/${takeSeq}`}
        className={cn(
          "inline-flex items-center justify-center p-1 rounded hover:bg-gray-700/50 transition-colors",
          "text-primary-400 hover:text-primary-300",
          className
        )}
      >
        <Activity className={iconSizes[size]} />
      </InternalLink>
    )
  }

  if (variant === 'minimal') {
    return (
      <InternalLink 
        to={`/take/${chainId}/${auctionAddress}/${roundId}/${takeSeq}`}
        className={cn(
          "font-mono text-primary-400 hover:text-primary-300 transition-colors",
          sizeClasses[size],
          className
        )}
      >
        {children || takeId}
      </InternalLink>
    )
  }

  // Default variant
  return (
    <InternalLink 
      to={`/take/${chainId}/${auctionAddress}/${roundId}/${takeSeq}`}
      className={cn(
        "inline-flex items-center space-x-1 text-primary-400 hover:text-primary-300 transition-colors font-mono",
        sizeClasses[size],
        className
      )}
    >
      <Activity className={iconSizes[size]} />
      <span>{children || takeId}</span>
    </InternalLink>
  )
}

export default TakeLink