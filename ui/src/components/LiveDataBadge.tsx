/**
 * LiveDataBadge component
 * Visual indicator for live blockchain data with pulsing animation
 */

import React from 'react'
import { clsx } from 'clsx'

interface LiveDataBadgeProps {
  isLive: boolean
  isLoading?: boolean
  className?: string
  variant?: 'small' | 'medium' | 'large'
}

export function LiveDataBadge({ 
  isLive, 
  isLoading = false, 
  className = '',
  variant = 'small'
}: LiveDataBadgeProps) {
  const sizeClasses = {
    small: 'px-1 py-0.5 text-xs',
    medium: 'px-1.5 py-0.5 text-xs',
    large: 'px-2 py-1 text-sm'
  }

  if (isLoading) {
    return (
      <span className={clsx(
        'inline-flex items-center rounded-full font-medium',
        'bg-gray-800/30 text-gray-400',
        sizeClasses[variant],
        className
      )}>
        <span className={clsx(
          'mr-1 h-1 w-1 rounded-full bg-gray-500',
          'animate-pulse'
        )} />
        ...
      </span>
    )
  }

  if (!isLive) {
    return null // Don't show badge if data is not live
  }

  return (
    <span className={clsx(
      'inline-flex items-center rounded-full font-medium',
      'bg-green-900/10 text-green-400/80 border border-green-800/20',
      sizeClasses[variant],
      className
    )}>
      <span className={clsx(
        'mr-1 h-1 w-1 rounded-full bg-green-500/70',
        'animate-pulse'
      )} />
      LIVE
    </span>
  )
}