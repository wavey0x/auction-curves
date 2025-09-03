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
    small: 'px-1.5 py-0.5 text-xs',
    medium: 'px-2 py-1 text-sm',
    large: 'px-3 py-1.5 text-base'
  }

  if (isLoading) {
    return (
      <span className={clsx(
        'inline-flex items-center rounded-full font-medium',
        'bg-gray-700 text-gray-300',
        sizeClasses[variant],
        className
      )}>
        <span className={clsx(
          'mr-1.5 h-1.5 w-1.5 rounded-full bg-gray-400',
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
      'bg-green-900/20 text-green-300 border border-green-800/30',
      sizeClasses[variant],
      className
    )}>
      <span className={clsx(
        'mr-1.5 h-1.5 w-1.5 rounded-full bg-green-400',
        'animate-pulse'
      )} />
      LIVE
    </span>
  )
}