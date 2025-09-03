/**
 * Clean Progress Bar Component
 * Simple, single-line progress bar that updates in place
 */

import React from 'react'
import { clsx } from 'clsx'

interface CleanProgressBarProps {
  progress: number // 0-100 percentage
  label?: string
  showPercentage?: boolean
  color?: 'blue' | 'green' | 'purple' | 'orange'
  size?: 'sm' | 'md' | 'lg'
  className?: string
  animate?: boolean
}

export function CleanProgressBar({
  progress,
  label,
  showPercentage = false,
  color = 'blue',
  size = 'md',
  className = '',
  animate = true
}: CleanProgressBarProps) {
  const colorClasses = {
    blue: 'bg-primary-500',
    green: 'bg-success-500', 
    purple: 'bg-purple-500',
    orange: 'bg-warning-500'
  }

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  }

  const normalizedProgress = Math.min(Math.max(progress, 0), 100)

  return (
    <div className={clsx('w-full', className)}>
      {(label || showPercentage) && (
        <div className="flex justify-between items-center mb-1">
          {label && (
            <span className="text-xs text-gray-400 font-medium">
              {label}
            </span>
          )}
          {showPercentage && (
            <span className="text-xs text-gray-400 font-medium">
              {normalizedProgress.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      
      <div className={clsx(
        'w-full bg-gray-700 rounded-full overflow-hidden',
        sizeClasses[size]
      )}>
        <div 
          className={clsx(
            'h-full rounded-full',
            colorClasses[color],
            animate && 'transition-all duration-500 ease-out'
          )}
          style={{ 
            width: `${normalizedProgress}%`
          }}
        />
      </div>
    </div>
  )
}