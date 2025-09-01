import React from 'react'
import { Clock, TrendingDown } from 'lucide-react'

interface StackedProgressMeterProps {
  timeProgress: number // 0-100, percentage of time elapsed
  amountProgress: number // 0-100, percentage of tokens sold
  timeRemaining?: number // seconds remaining
  totalTakes: number // number of takes
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const StackedProgressMeter: React.FC<StackedProgressMeterProps> = ({
  timeProgress,
  amountProgress,
  timeRemaining,
  totalTakes,
  className = '',
  size = 'md'
}) => {
  const heights = {
    sm: 'h-1',
    md: 'h-1.5',
    lg: 'h-2'
  }
  
  const spacing = {
    sm: 'space-y-1',
    md: 'space-y-1.5',
    lg: 'space-y-2'
  }

  const height = heights[size]
  const gap = spacing[size]

  return (
    <div className={`text-sm ${gap} ${className}`}>
      {/* Time Progress Bar */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-blue-400 font-medium">Time</span>
          <span className="text-xs text-blue-400 font-medium">{timeProgress.toFixed(0)}%</span>
        </div>
        <div className={`w-full bg-gray-700 rounded-full ${height}`}>
          <div 
            className="bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all duration-500 ease-out"
            style={{ 
              width: `${Math.min(timeProgress, 100)}%`,
              height: '100%'
            }}
          ></div>
        </div>
      </div>

      {/* Amount Sold Progress Bar */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-green-400 font-medium">Taken ({totalTakes})</span>
          <span className="text-xs text-green-400 font-medium">{amountProgress.toFixed(0)}%</span>
        </div>
        <div className={`w-full bg-gray-700 rounded-full ${height}`}>
          <div 
            className="bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all duration-500 ease-out"
            style={{ 
              width: `${Math.min(amountProgress, 100)}%`,
              height: '100%'
            }}
          ></div>
        </div>
      </div>

      {/* Progress Relationship Indicator */}
      {size !== 'sm' && (
        <div className="flex items-center justify-center mt-2">
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            {amountProgress > timeProgress ? (
              <>
                <div className="h-1 w-1 bg-green-400 rounded-full animate-pulse"></div>
                <span>Fast selling</span>
              </>
            ) : amountProgress < timeProgress - 10 ? (
              <>
                <div className="h-1 w-1 bg-yellow-400 rounded-full animate-pulse"></div>
                <span>Slow selling</span>
              </>
            ) : (
              <>
                <div className="h-1 w-1 bg-gray-400 rounded-full"></div>
                <span>Normal pace</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default StackedProgressMeter