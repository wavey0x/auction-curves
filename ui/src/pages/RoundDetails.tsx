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
import TakesTable from '../components/TakesTable'
import StatsCard from '../components/StatsCard'
import StackedProgressMeter from '../components/StackedProgressMeter'
import LoadingSpinner from '../components/LoadingSpinner'
import AddressDisplay from '../components/AddressDisplay'
import { formatAddress, formatTokenAmount, formatReadableTokenAmount, formatUSD, formatTimeAgo } from '../lib/utils'

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
  const { data: takes, isLoading: takesLoading } = useQuery({
    queryKey: ['auctionTakes', chainId, auctionAddress, roundId],
    queryFn: () => apiClient.getAuctionTakes(auctionAddress!, parseInt(chainId!), parseInt(roundId!)),
    enabled: !!chainId && !!auctionAddress && !!roundId
  })

  // Fetch rounds data to get specific round info (use the from_token from takes)
  const { data: roundsData, isLoading: roundsLoading } = useQuery({
    queryKey: ['auctionRounds', chainId, auctionAddress, takes?.[0]?.from_token],
    queryFn: async () => {
      if (takes && takes.length > 0) {
        return apiClient.getAuctionRounds(auctionAddress!, parseInt(chainId!), takes[0].from_token)
      }
      return null
    },
    enabled: !!chainId && !!auctionAddress && !!takes && takes.length > 0
  })

  // Fetch tokens for symbol resolution
  const { data: tokens } = useQuery({
    queryKey: ['tokens'],
    queryFn: apiClient.getTokens
  })

  const isLoading = detailsLoading || takesLoading || roundsLoading

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (!auctionDetails || !takes) {
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
  
  // Find the specific round data from the rounds API
  const specificRound = roundsData?.rounds?.find(r => r.round_id.toString() === roundId)
  
  const roundInfo = isCurrentRound ? currentRound : specificRound ? {
    round_id: specificRound.round_id,
    kicked_at: specificRound.kicked_at,
    round_start: specificRound.round_start,
    round_end: specificRound.round_end,
    initial_available: specificRound.initial_available,
    is_active: specificRound.is_active,
    total_takes: specificRound.total_takes || takes.length,
    seconds_elapsed: specificRound.round_start ? Math.floor(Date.now() / 1000) - specificRound.round_start : 0,
    progress_percentage: specificRound.is_active ? 
      (specificRound.total_takes || takes.length) / Math.max(1, parseFloat(specificRound.initial_available)) * 100 
      : 100
  } : {
    // Fallback if no round data found
    round_id: parseInt(roundId!),
    kicked_at: new Date().toISOString(),
    initial_available: "0",
    is_active: false,
    total_takes: takes.length,
    seconds_elapsed: 3600,
    progress_percentage: 100
  }
  
  // Calculate time remaining using round_end timestamp, ensuring it floors to 0
  const timeRemaining = roundInfo.round_end 
    ? Math.max(0, roundInfo.round_end - Math.floor(Date.now() / 1000))
    : roundInfo.time_remaining || 0
  
  // Calculate time progress (0-100%) from round start to round end
  const calculateTimeProgress = () => {
    if (!roundInfo.round_start || !roundInfo.round_end) {
      return roundInfo.is_active ? 0 : 100
    }
    
    const totalDuration = roundInfo.round_end - roundInfo.round_start
    const elapsed = Math.floor(Date.now() / 1000) - roundInfo.round_start
    
    if (totalDuration <= 0) return 100
    
    const progress = Math.min(100, Math.max(0, (elapsed / totalDuration) * 100))
    return progress
  }
  
  const timeProgress = calculateTimeProgress()

  const fromTokens = auctionDetails.from_tokens
  const wantToken = auctionDetails.want_token

  // Calculate round statistics
  const totalAmountSold = takes.reduce((sum, sale) => sum + parseFloat(sale.amount_taken), 0)
  const totalVolume = takes.reduce((sum, sale) => sum + parseFloat(sale.amount_paid), 0)
  const avgPrice = takes.length > 0 ? takes.reduce((sum, sale) => sum + parseFloat(sale.price), 0) / takes.length : 0
  const uniqueTakers = new Set(takes.map(sale => sale.taker)).size

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
              <div className="flex items-center space-x-2">
                <span>Auction</span>
                <AddressDisplay
                  address={auctionAddress!}
                  chainId={parseInt(chainId!)}
                  showExternalLink={false}
                  className="text-primary-400 hover:text-primary-300"
                />
              </div>
              <span>•</span>
              <span>
                {takes.length > 0 && takes[0].from_token_symbol ? 
                  `${takes[0].from_token_symbol} → ${wantToken.symbol}` : 
                  `${fromTokens[0]?.symbol || '?'} → ${wantToken.symbol}`
                }
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* Round Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Takes"
          value={takes.length}
          icon={Activity}
          iconColor="text-primary-500"
        />
        
        <StatsCard
          title="Amount Taken"
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
            {roundInfo.is_active ? (
              <div className="h-2 w-2 rounded-full bg-success-500 animate-pulse"></div>
            ) : (
              <div className="h-2 w-2 rounded-full bg-gray-600"></div>
            )}
            <span>Round Information</span>
            {roundInfo.is_active && (
              <div className="px-2 py-0.5 rounded-full text-xs font-medium bg-success-500/20 text-success-400">
                ACTIVE
              </div>
            )}
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
              </div>
            </div>

            <div>
              <div className="space-y-4">
                <div>
                  <span className="text-sm text-gray-500">Initial Available</span>
                  <div className="font-mono text-gray-200">
                    {formatReadableTokenAmount(roundInfo.initial_available, 4)} {fromTokens[0]?.symbol || ''}
                  </div>
                </div>

                {roundInfo.is_active && timeRemaining > 0 && (
                  <div>
                    <span className="text-sm text-gray-500">Time Remaining</span>
                    <div className="text-gray-200 font-medium">
                      {timeRemaining >= 3600 ? (
                        `${Math.floor(timeRemaining / 3600)}h ${Math.floor((timeRemaining % 3600) / 60)}m`
                      ) : (
                        `${Math.floor(timeRemaining / 60)}m ${timeRemaining % 60}s`
                      )}
                    </div>
                  </div>
                )}

                {roundInfo.current_price && (
                  <div>
                    <span className="text-sm text-gray-500">Current Price</span>
                    <div className="font-mono text-gray-200">
                      {formatReadableTokenAmount(roundInfo.current_price, 6)}
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
                      {avgPrice.toFixed(6)} {auctionDetails.want_token.symbol}
                    </div>
                    <div className="text-xs text-gray-500">
                      per {auctionDetails.from_tokens[0]?.symbol || 'token'}
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
                timeProgress={timeProgress}
                amountProgress={roundInfo.progress_percentage}
                timeRemaining={timeRemaining}
                totalTakes={roundInfo.total_takes}
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
              to={`/auction/${chainId}/${auctionAddress}`}
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
          
          {/* Auction Parameters */}
          <div className="mt-6 pt-4 border-t border-gray-800">
            <h4 className="text-sm font-medium text-gray-400 mb-3">Auction Parameters</h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Update Interval</span>
                <span className="text-gray-300">
                  {auctionDetails.parameters?.price_update_interval || 'N/A'}s
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Auction Length</span>
                <span className="text-gray-300">
                  {auctionDetails.parameters?.auction_length || 'N/A'}s
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Decay Rate</span>
                <span className="text-gray-300 font-mono">
                  {auctionDetails.parameters?.decay_rate ? 
                    `${(auctionDetails.parameters.decay_rate * 100).toFixed(3)}%` : 
                    'N/A'
                  }
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Starting Price</span>
                <span className="text-gray-300 font-mono">
                  {auctionDetails.parameters?.starting_price && auctionDetails.parameters.starting_price !== "0" ? 
                    auctionDetails.parameters.starting_price : 
                    'Dynamic'
                  }
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Takes Table */}
      {takes.length > 0 ? (
        <TakesTable
          takes={takes}
          title={`Takes in Round R${roundId}`}
          tokens={tokens?.tokens || []}
          maxHeight="max-h-[600px]"
        />
      ) : (
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <TrendingDown className="h-8 w-8 text-gray-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-400 mb-2">No Takes Yet</h3>
          <p className="text-gray-600 max-w-md mx-auto">
            {roundInfo.is_active 
              ? "This round is active but no takes have occurred yet." 
              : "This round completed without any takes."
            }
          </p>
        </div>
      )}
    </div>
  )
}

export default RoundDetails