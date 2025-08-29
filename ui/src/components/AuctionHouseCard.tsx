import React from 'react'
import { Link } from 'react-router-dom'
import { 
  Clock, 
  TrendingUp, 
  TrendingDown, 
  Users, 
  DollarSign,
  Coins,
  Activity
} from 'lucide-react'
import type { AuctionListItem } from '../types/auction'
import { formatAddress, formatTokenAmount, formatUSD, formatTimeAgo } from '../lib/utils'
import StackedProgressMeter from './StackedProgressMeter'

interface AuctionCardProps {
  auction: AuctionListItem
}

const AuctionCard: React.FC<AuctionCardProps> = ({ auction }) => {
  const isActive = auction.current_round?.is_active || false
  const currentRound = auction.current_round
  
  return (
    <Link to={`/auction-house/${auctionHouse.address}`}>
      <div className="card hover:bg-gray-800/50 transition-colors group">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${
              isActive ? 'bg-success-500/20' : 'bg-gray-700'
            }`}>
              <Activity className={`h-5 w-5 ${
                isActive ? 'text-success-400' : 'text-gray-400'
              }`} />
            </div>
            <div>
              <h3 className="font-mono text-sm font-medium text-gray-200 group-hover:text-primary-400 transition-colors">
                {formatAddress(auctionHouse.address, 8)}
              </h3>
              <p className="text-xs text-gray-500">
                Auction House
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className={`h-2 w-2 rounded-full ${
              isActive ? 'bg-success-500 animate-pulse' : 'bg-gray-600'
            }`}></div>
            <span className={`text-xs font-medium uppercase ${
              isActive ? 'text-success-400' : 'text-gray-500'
            }`}>
              {isActive ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>

        {/* Token Information */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-500 uppercase">Trading</span>
            <span className="text-xs text-gray-600">→</span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1">
              <Coins className="h-3 w-3 text-primary-500" />
              <div className="flex flex-wrap gap-1">
                {auctionHouse.from_tokens.map((token, index) => (
                  <span key={token.address} className="text-xs font-medium text-primary-400">
                    {token.symbol}
                    {index < auctionHouse.from_tokens.length - 1 ? ',' : ''}
                  </span>
                ))}
              </div>
            </div>
            
            <div className="flex items-center space-x-1">
              <Coins className="h-3 w-3 text-yellow-500" />
              <span className="text-xs font-medium text-yellow-400">
                {auctionHouse.want_token.symbol}
              </span>
            </div>
          </div>
        </div>

        {/* Current Round Info */}
        {currentRound && (
          <div className="mb-4 p-3 bg-gray-800/30 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-400">
                Round R{currentRound.round_id}
              </span>
              <span className="text-xs text-gray-500">
                {currentRound.total_sales} sales
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-xs">
              {currentRound.current_price && (
                <div>
                  <span className="text-gray-500">Current Price</span>
                  <div className="font-mono text-gray-200">
                    {formatTokenAmount(currentRound.current_price, 6, 2)}
                  </div>
                </div>
              )}
              
              {currentRound.time_remaining && (
                <div>
                  <span className="text-gray-500">Time Left</span>
                  <div className="font-medium text-primary-400">
                    {Math.floor(currentRound.time_remaining / 60)}m
                  </div>
                </div>
              )}
            </div>

            {currentRound.progress_percentage && currentRound.time_remaining && (
              <div className="mt-2">
                <span className="text-xs text-gray-500 mb-2 block">Progress</span>
                <StackedProgressMeter
                  timeProgress={(currentRound.seconds_elapsed / (currentRound.seconds_elapsed + currentRound.time_remaining)) * 100}
                  amountProgress={currentRound.progress_percentage}
                  timeRemaining={currentRound.time_remaining}
                  totalSales={currentRound.total_sales}
                  size="sm"
                />
              </div>
            )}
          </div>
        )}

        {/* Parameters */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-gray-500 flex items-center space-x-1">
              <TrendingDown className="h-3 w-3" />
              <span>Decay Rate</span>
            </span>
            <div className="font-medium text-gray-200">
              {auctionHouse.decay_rate_percent.toFixed(1)}%
            </div>
          </div>
          
          <div>
            <span className="text-gray-500 flex items-center space-x-1">
              <Clock className="h-3 w-3" />
              <span>Update Interval</span>
            </span>
            <div className="font-medium text-gray-200">
              {auctionHouse.update_interval_minutes.toFixed(1)}m
            </div>
          </div>
        </div>

        {/* Footer */}
        {auctionHouse.last_kicked && (
          <div className="mt-4 pt-3 border-t border-gray-800">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Last Round</span>
              <span>{formatTimeAgo(new Date(auctionHouse.last_kicked).getTime() / 1000)}</span>
            </div>
          </div>
        )}
      </div>
    </Link>
  )
}

export default AuctionHouseCard