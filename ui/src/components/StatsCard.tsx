import React from 'react'
import { LucideIcon } from 'lucide-react'
import { cn } from '../lib/utils'

interface StatsCardProps {
  title: string
  value: string | number
  change?: {
    value: number
    type: 'increase' | 'decrease'
    period: string
  }
  icon: LucideIcon
  iconColor?: string
  trend?: {
    data: number[]
    color?: string
  }
  loading?: boolean
}

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  change,
  icon: Icon,
  iconColor = 'text-primary-500',
  trend,
  loading = false
}) => {
  if (loading) {
    return (
      <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-lg px-3 py-2 shadow-lg animate-pulse">
        <div className="text-center">
          <div className="h-3 bg-gray-800 rounded w-16 mx-auto mb-1"></div>
          <div className="h-5 bg-gray-800 rounded w-12 mx-auto"></div>
          {change && <div className="h-3 bg-gray-800 rounded w-20 mx-auto mt-1"></div>}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-lg px-3 py-2 shadow-lg group hover:bg-gray-800/50 transition-all duration-200">
      <div className="text-center">
        <p className="text-xs font-mono text-gray-400 mb-1">{title}</p>
        
        <div className="flex justify-center">
          <p className="text-lg font-mono font-bold text-gray-100">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
        </div>
        
        {change && (
          <div className="mt-1 flex justify-center">
            <span
              className={cn(
                "inline-flex items-center text-xs font-mono",
                change.type === 'increase' 
                  ? "text-success-400" 
                  : "text-danger-400"
              )}
            >
              {change.type === 'increase' ? '+' : '-'}
              {Math.abs(change.value)}%
            </span>
            <span className="text-xs font-mono text-gray-500 ml-1">
              vs {change.period}
            </span>
          </div>
        )}
      </div>
      
      {/* Simple trend line */}
      {trend && trend.data.length > 1 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <div className="flex items-end space-x-1 h-8">
            {trend.data.map((point, index) => {
              const maxValue = Math.max(...trend.data)
              const height = maxValue > 0 ? (point / maxValue) * 100 : 0
              
              return (
                <div
                  key={index}
                  className={cn(
                    "flex-1 rounded-t transition-all duration-200 hover:opacity-80",
                    trend.color || "bg-primary-500/30"
                  )}
                  style={{ height: `${height}%` }}
                />
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default StatsCard