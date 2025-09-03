import React from 'react'
import { Clock, TrendingDown } from 'lucide-react'
import { CleanProgressBar } from './CleanProgressBar'

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
  return (
    <div className={`space-y-2 ${className}`}>
      {/* Time Progress */}
      <CleanProgressBar
        progress={timeProgress}
        label="Time"
        showPercentage={true}
        color="blue"
        size={size}
      />
      
      {/* Volume Progress with Take Count */}  
      <CleanProgressBar
        progress={amountProgress}
        label={`Takes (${totalTakes})`}
        showPercentage={true}
        color="green"
        size={size}
      />
    </div>
  )
}

export default StackedProgressMeter