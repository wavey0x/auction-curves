import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  ArrowLeft,
  Clock,
  TrendingDown, 
  TrendingUp, 
  Users, 
  DollarSign,
  Activity,
  Target,
  Zap,
  AlertCircle
} from 'lucide-react'
import { apiClient } from '../lib/api'
import SalesTable from '../components/SalesTable'
import StatsCard from '../components/StatsCard'
import StackedProgressMeter from '../components/StackedProgressMeter'
import LoadingSpinner from '../components/LoadingSpinner'
import { formatAddress, formatTokenAmount, formatUSD, formatTimeAgo } from '../lib/utils'

const RoundDetails: React.FC = () => {
  const { chainId, auctionAddress, roundId } = useParams<{
    chainId: string
    auctionAddress: string
    roundId: string
  }>()

  // Fetch auction details
  const { data: auctionDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['auction', chainId, auctionAddress],
    queryFn: () => apiClient.getAuction(auctionAddress!, parseInt(chainId!)),
    enabled: !!chainId && !!auctionAddress
  })

  // Fetch takes for this specific round
  const { data: sales, isLoading: salesLoading } = useQuery({
    queryKey: ['auctionTakes', chainId, auctionAddress, roundId],
    queryFn: () => apiClient.getAuctionTakes(auctionAddress!, parseInt(chainId!), parseInt(roundId!)),
    enabled: !!chainId && !!auctionAddress && !!roundId
  })

  // Fetch tokens for symbol resolution
  const { data: tokens } = useQuery({
    queryKey: ['tokens'],
    queryFn: apiClient.getTokens
  })

  const isLoading = detailsLoading || salesLoading

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (!auctionDetails || !sales) {
    return (
      <div className="card text-center py-12">
        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="h-8 w-8 text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-400 mb-2">Round Not Found</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          The requested auction round could not be found.
        </p>
        <Link 
          to="/" 
          className="inline-flex items-center space-x-2 mt-4 text-primary-400 hover:text-primary-300"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </Link>
      </div>
    )
  }

  const currentRound = auctionDetails.current_round
  const isCurrentRound = currentRound && currentRound.round_id.toString() === roundId
  const roundInfo = isCurrentRound ? currentRound : {
    round_id: parseInt(roundId!),
    kicked_at: new Date().toISOString(),
    initial_available: "0",
    is_active: false,
    total_sales: sales.length,
    seconds_elapsed: 3600,
    progress_percentage: 100
  }

  const fromTokens = auctionDetails.from_tokens
  const wantToken = auctionDetails.want_token

  // Calculate round statistics
  const totalAmountSold = sales.reduce((sum, sale) => sum + parseFloat(sale.amount_taken), 0)
  const totalVolume = sales.reduce((sum, sale) => sum + parseFloat(sale.amount_paid), 0)
  const avgPrice = sales.length > 0 ? sales.reduce((sum, sale) => sum + parseFloat(sale.price), 0) / sales.length : 0
  const uniqueTakers = new Set(sales.map(sale => sale.taker)).size

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link 
            to="/" 
            className="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-gray-200">
                Round R{roundId}
              </h1>
              <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                roundInfo.is_active 
                  ? 'bg-success-500/20 text-success-400' 
                  : 'bg-gray-700 text-gray-400'
              }`}>
                {roundInfo.is_active ? 'Active' : 'Completed'}
              </div>
            </div>
            
            <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
              <Link 
                to={`/auction/${chainId}/${auctionAddress}`}
                className="hover:text-primary-400 transition-colors"
              >
                Auction {formatAddress(auctionAddress!, 8)}
              </Link>
              <span>•</span>
              <span>
                {fromTokens.map(t => t.symbol).join(', ')} → {wantToken.symbol}
              </span>
            </div>
          </div>
        </div>

        {roundInfo.is_active && roundInfo.time_remaining && (
          <div className="text-right">
            <div className="text-lg font-semibold text-success-400">
              {Math.floor(roundInfo.time_remaining / 60)}m {roundInfo.time_remaining % 60}s
            </div>
            <div className="text-sm text-gray-500">Time Remaining</div>
          </div>
        )}
      </div>

      {/* Round Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Sales"
          value={sales.length}
          icon={Activity}
          iconColor="text-primary-500"
        />
        
        <StatsCard
          title="Amount Sold"
          value={formatTokenAmount(totalAmountSold.toString(), 18, 2)}
          icon={TrendingDown}
          iconColor="text-success-500"
        />
        
        <StatsCard
          title="Volume"
          value={formatTokenAmount(totalVolume.toString(), 6, 2)}
          icon={DollarSign}
          iconColor="text-yellow-500"
        />
        
        <StatsCard
          title="Unique Takers"
          value={uniqueTakers}
          icon={Users}
          iconColor="text-purple-500"
        />
      </div>

      {/* Round Details Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
            <Target className="h-5 w-5 text-primary-500" />
            <span>Round Information</span>
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="space-y-4">
                <div>
                  <span className="text-sm text-gray-500">Round ID</span>
                  <div className="font-mono text-lg font-medium text-primary-400">
                    R{roundInfo.round_id}
                  </div>
                </div>
                
                <div>
                  <span className="text-sm text-gray-500">Kicked At</span>
                  <div className="text-gray-200">
                    {new Date(roundInfo.kicked_at).toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatTimeAgo(new Date(roundInfo.kicked_at).getTime() / 1000)}
                  </div>
                </div>

                <div>
                  <span className="text-sm text-gray-500">Status</span>
                  <div className="flex items-center space-x-2">
                    <div className={`h-2 w-2 rounded-full ${
                      roundInfo.is_active ? 'bg-success-500 animate-pulse' : 'bg-gray-600'
                    }`}></div>
                    <span className={`font-medium ${
                      roundInfo.is_active ? 'text-success-400' : 'text-gray-400'
                    }`}>
                      {roundInfo.is_active ? 'Active' : 'Completed'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <div className="space-y-4">
                <div>
                  <span className="text-sm text-gray-500">Initial Available</span>
                  <div className="font-mono text-gray-200">
                    {formatTokenAmount(roundInfo.initial_available, 18, 4)}
                  </div>
                </div>

                {roundInfo.current_price && (
                  <div>
                    <span className="text-sm text-gray-500">Current Price</span>
                    <div className="font-mono text-gray-200">
                      {formatTokenAmount(roundInfo.current_price, 6, 6)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {formatUSD(parseFloat(roundInfo.current_price) * 1.5)}
                    </div>
                  </div>
                )}

                {avgPrice > 0 && (
                  <div>
                    <span className="text-sm text-gray-500">Average Sale Price</span>
                    <div className="font-mono text-gray-200">
                      {formatTokenAmount(avgPrice.toString(), 6, 6)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {formatUSD(avgPrice * 1.5)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Stacked Progress Meters */}
          {roundInfo.progress_percentage !== undefined && (
            <div className="mt-6">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Round Progress</h4>
              <StackedProgressMeter
                timeProgress={roundInfo.is_active && roundInfo.time_remaining ? 
                  (roundInfo.seconds_elapsed / (roundInfo.seconds_elapsed + roundInfo.time_remaining)) * 100 : 100
                }
                amountProgress={roundInfo.progress_percentage}
                timeRemaining={roundInfo.time_remaining}
                totalSales={roundInfo.total_sales}
                size="lg"
              />
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            <span>Quick Actions</span>
          </h3>
          
          <div className="space-y-3">
            <Link
              to={`/auction/${auctionAddress}`}
              className="block w-full p-3 text-center bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <div className="text-sm font-medium text-gray-200">View Auction</div>
              <div className="text-xs text-gray-500">See all rounds</div>
            </Link>
            
            {roundInfo.is_active && (
              <button className="block w-full p-3 text-center bg-primary-500/20 hover:bg-primary-500/30 text-primary-400 rounded-lg transition-colors">
                <div className="text-sm font-medium">Participate</div>
                <div className="text-xs text-primary-500">Take tokens</div>
              </button>
            )}
            
            <button className="block w-full p-3 text-center bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
              <div className="text-sm font-medium text-gray-200">Export Data</div>
              <div className="text-xs text-gray-500">Download CSV</div>
            </button>
          </div>
          
          {/* Round Parameters */}
          <div className="mt-6 pt-4 border-t border-gray-800">
            <h4 className="text-sm font-medium text-gray-400 mb-3">Parameters</h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Update Interval</span>
                <span className="text-gray-300">{auctionDetails.price_update_interval}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Auction Length</span>
                <span className="text-gray-300">{auctionDetails.auction_length}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Step Decay</span>
                <span className="text-gray-300 font-mono">
                  {(parseFloat(auctionDetails.step_decay) / 1e27 * 100).toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sales Table */}
      {sales.length > 0 ? (
        <SalesTable
          sales={sales}
          title={`Sales in Round R${roundId}`}
          tokens={tokens?.tokens || []}
          maxHeight="max-h-[600px]"
        />
      ) : (
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <TrendingDown className="h-8 w-8 text-gray-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-400 mb-2">No Sales Yet</h3>
          <p className="text-gray-600 max-w-md mx-auto">
            {roundInfo.is_active 
              ? "This round is active but no sales have occurred yet." 
              : "This round completed without any sales."
            }
          </p>
        </div>
      )}
    </div>
  )
}

export default RoundDetails