import React from 'react'
import { Link } from 'react-router-dom'
import { TrendingDown, Clock, DollarSign, Activity } from 'lucide-react'
import type { AuctionSummary } from '../types/auction'
import {
  formatAddress,
  formatTokenAmount,
  formatUSD,
  formatTimeAgo,
  getAuctionProgress,
  getAuctionStatus,
  cn
} from '../lib/utils'

interface AuctionCardProps {
  auction: AuctionSummary
}

const AuctionCard: React.FC<AuctionCardProps> = ({ auction }) => {
  const createdAt = new Date(auction.created_at).getTime() / 1000
  const progress = getAuctionProgress(createdAt, 86400) // Assuming 24h default
  const status = getAuctionStatus(progress)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-success-400 bg-success-500/20'
      case 'ending':
        return 'text-warning-400 bg-warning-500/20'
      case 'ended':
        return 'text-gray-400 bg-gray-500/20'
      default:
        return 'text-gray-400 bg-gray-500/20'
    }
  }

  return (
    <Link to={`/auction/${auction.address}`} className="block group">
      <div className="card hover:bg-gray-800/50 transition-all duration-200 group-hover:scale-[1.02] group-hover:shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <h3 className="font-mono text-sm text-gray-300">
                {formatAddress(auction.address, 10)}
              </h3>
              <span className={cn("badge text-xs", getStatusColor(status))}>
                {status}
              </span>
            </div>
            
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span>Want:</span>
              <span className="font-mono text-gray-300">
                {formatAddress(auction.want_token, 8)}
              </span>
            </div>
          </div>
          
        </div>

        {/* Progress bar for active auctions */}
        {status === 'active' && progress > 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>Progress</span>
              <span>{progress.toFixed(1)}%</span>
            </div>
            <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <TrendingDown className="h-4 w-4 text-success-500" />
              <div>
                <div className="text-xs text-gray-500">Kicks</div>
                <div className="font-semibold text-success-400">
                  {auction.total_kicks}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Activity className="h-4 w-4 text-primary-500" />
              <div>
                <div className="text-xs text-gray-500">Takes</div>
                <div className="font-semibold text-primary-400">
                  {auction.total_takes}
                </div>
              </div>
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <DollarSign className="h-4 w-4 text-yellow-500" />
              <div>
                <div className="text-xs text-gray-500">Volume</div>
                <div className="font-semibold text-yellow-400">
                  {formatUSD(auction.total_volume)}
                </div>
              </div>
            </div>
            
            {auction.current_price && (
              <div className="flex items-center space-x-2">
                <div className="h-4 w-4 bg-purple-500 rounded-full flex-shrink-0" />
                <div>
                  <div className="text-xs text-gray-500">Current Price</div>
                  <div className="font-semibold text-purple-400 font-mono text-xs">
                    {formatTokenAmount(auction.current_price, 18, 6)}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-800">
          <div className="flex items-center space-x-1 text-xs text-gray-500">
            <Clock className="h-3 w-3" />
            <span>Created {formatTimeAgo(createdAt)}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className={cn(
              "h-2 w-2 rounded-full",
              status === 'active' ? 'bg-success-500 animate-pulse' : 
              status === 'ending' ? 'bg-warning-500 animate-pulse' :
              'bg-gray-500'
            )} />
            <span className="text-xs text-gray-500 capitalize">{status}</span>
          </div>
        </div>
      </div>
    </Link>
  )
}

export default AuctionCard