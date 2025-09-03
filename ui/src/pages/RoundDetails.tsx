import React, { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Clock,
  TrendingDown, 
  TrendingUp, 
  Users, 
  DollarSign,
  Activity,
  Target,
  Zap,
  AlertCircle,
  Package
} from 'lucide-react'
import { apiClient } from '../lib/api'
import TakesTable from '../components/TakesTable'
import StatsCard from '../components/StatsCard'
import StackedProgressMeter from '../components/StackedProgressMeter'
import LoadingSpinner from '../components/LoadingSpinner'
import AddressDisplay from '../components/AddressDisplay'
import BackButton from '../components/BackButton'
import InternalLink from '../components/InternalLink'
import RoundLink from '../components/RoundLink'
import { LiveDataBadge } from '../components/LiveDataBadge'
import { useAuctionLiveData } from '../hooks/useAuctionLiveData'
import { formatAddress, formatTokenAmount, formatReadableTokenAmount, formatUSD, formatTimeAgo, getTxLink } from '../lib/utils'

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
  const { data: takesResponse, isLoading: takesLoading } = useQuery({
    queryKey: ['auctionTakes', chainId, auctionAddress, roundId],
    queryFn: () => apiClient.getAuctionTakes(auctionAddress!, parseInt(chainId!), parseInt(roundId!)),
    enabled: !!chainId && !!auctionAddress && !!roundId
  })

  // Extract takes array from paginated response
  const takes = takesResponse?.takes || []

  // Fetch specific round data directly by round ID
  const { data: specificRoundData, isLoading: roundsLoading } = useQuery({
    queryKey: ['auctionRound', chainId, auctionAddress, roundId],
    queryFn: async () => {
      if (!chainId || !auctionAddress || !roundId) return null;
      
      try {
        // Get the specific round directly by ID
        const roundData = await apiClient.getAuctionRound(
          auctionAddress!, 
          parseInt(chainId!), 
          parseInt(roundId!)
        );
        return roundData;
      } catch (error) {
        console.log(`Failed to fetch round ${roundId}:`, error);
        return null;
      }
    },
    enabled: !!chainId && !!auctionAddress && !!roundId
  })

  // Fetch tokens for symbol resolution
  const { data: tokens } = useQuery({
    queryKey: ['tokens'],
    queryFn: apiClient.getTokens
  })

  // Calculate values needed for other hooks (must be before any early returns)
  const currentRound = auctionDetails?.current_round
  const isCurrentRound = currentRound && currentRound.round_id.toString() === roundId
  // specificRoundData now contains the direct round data
  const specificRound = specificRoundData
  
  // Get live data for this specific round
  // Now we should have the exact from_token for this specific round
  const fromTokenAddress = useMemo(() => {
    // Use the specific round data first - this should have the exact from_token for round 29
    if (specificRound?.from_token) {
      return specificRound.from_token;
    }
    // Fallback to first take from this round
    if (takes?.[0]?.from_token) {
      return takes[0].from_token;
    }
    // Final fallback to auction's first from_token
    return auctionDetails?.from_tokens?.[0]?.address || ''
  }, [specificRound?.from_token, takes, auctionDetails?.from_tokens])

  const { data: liveData, isLoading: liveDataLoading } = useAuctionLiveData(
    auctionAddress || '',
    fromTokenAddress,
    parseInt(chainId || '0'),
    30000 // 30 second refresh
  )


  // Calculate loading state after all hooks
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

  if (!auctionDetails || !takesResponse) {
    return (
      <div className="card text-center py-12">
        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="h-8 w-8 text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-400 mb-2">Round Not Found</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          The requested auction round could not be found.
        </p>
        <div className="mt-4">
          <BackButton />
        </div>
      </div>
    )
  }
  
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
  
  // Get the correct token symbol for this specific round
  const fromTokenSymbol = fromTokens.find(t => 
    t.address.toLowerCase() === fromTokenAddress.toLowerCase()
  )?.symbol || fromTokenAddress.slice(0,6) + "…" + fromTokenAddress.slice(-4)

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
          <BackButton />

          <h1 className="text-2xl font-bold text-gray-100">Round R{roundId}</h1>
        </div>
      </div>

      {/* Round Details Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <h3 className="text-lg font-semibold mb-4 flex items-center justify-center space-x-3">
            <div className={`h-2 w-2 rounded-full ${
              roundInfo.is_active 
                ? "bg-success-500 animate-pulse" 
                : "bg-gray-600"
            }`}></div>
            <span>Round Info</span>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
              roundInfo.is_active 
                ? "bg-success-500/20 text-success-400" 
                : "bg-gray-700 text-gray-400"
            }`}>
              {roundInfo.is_active ? "ACTIVE" : "COMPLETED"}
            </div>
          </h3>
          
          <div className="border-b border-gray-800 mb-6"></div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="space-y-4">
                <div>
                  <span className="text-sm text-gray-500">Round ID</span>
                  <div className="font-mono text-sm text-white">
                    R{roundInfo.round_id}
                  </div>
                </div>
                
                <div>
                  <span className="text-sm text-gray-500">Auction</span>
                  <div>
                    <InternalLink
                      to={`/auction/${chainId}/${auctionAddress}`}
                      variant="address"
                      className="font-mono text-sm"
                      address={auctionAddress!}
                      chainId={parseInt(chainId!)}
                    >
                      {formatAddress(auctionAddress!)}
                    </InternalLink>
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
                  <span className="text-sm text-gray-500">Initial Available</span>
                  <div className="font-mono text-gray-200">
                    {formatReadableTokenAmount(roundInfo.initial_available, 4)} {fromTokenSymbol}
                  </div>
                </div>

                <div>
                  <span className="text-sm text-gray-500">Kick Transaction</span>
                  <div className="font-mono text-sm">
                    {roundInfo.transaction_hash ? (
                      <a 
                        href={getTxLink(roundInfo.transaction_hash, parseInt(chainId!))}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-white hover:text-primary-300 transition-colors"
                      >
                        {formatAddress(roundInfo.transaction_hash)}
                      </a>
                    ) : (
                      <span className="text-gray-500">—</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div>
              <div className="space-y-4">
                <div>
                  <span className="text-sm text-gray-500">Token Pair</span>
                  <div className="text-sm text-gray-200">
                    <span className="text-gray-300 font-medium">
                      {fromTokenSymbol}
                    </span>
                    <span className="text-gray-400 mx-2 text-xl">→</span>
                    <span className="text-white font-medium">
                      {wantToken.symbol}
                    </span>
                  </div>
                </div>

                {/* Live Current Price */}
                {roundInfo.is_active && (
                  <div>
                    <span className="text-sm text-gray-500">Current Price</span>
                    <div className="flex items-center space-x-2">
                      {liveDataLoading ? (
                        <div className="flex items-center space-x-1">
                          <div className="animate-pulse h-2 w-2 bg-primary-400 rounded-full"></div>
                          <span className="text-xs text-gray-400">Loading...</span>
                        </div>
                      ) : liveData?.error ? (
                        <span className="text-red-400 text-xs">Error fetching live data</span>
                      ) : liveData?.amountNeeded !== undefined ? (
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-gray-200">
                            {formatTokenAmount(Number(liveData.amountNeeded), 18, 4)} {wantToken.symbol}
                          </span>
                          <LiveDataBadge isLive={true} variant="small" />
                        </div>
                      ) : (
                        <span className="text-gray-500 text-sm">—</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Live Available Amount */}
                {roundInfo.is_active && (
                  <div>
                    <span className="text-sm text-gray-500">Available</span>
                    <div className="flex items-center space-x-2">
                      {liveDataLoading ? (
                        <div className="flex items-center space-x-1">
                          <div className="animate-pulse h-2 w-2 bg-primary-400 rounded-full"></div>
                          <span className="text-xs text-gray-400">Loading...</span>
                        </div>
                      ) : liveData?.error ? (
                        <span className="text-red-400 text-xs">Error fetching live data</span>
                      ) : liveData?.available !== undefined ? (
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-gray-200">
                            {formatTokenAmount(Number(liveData.available), 18, 4)} {fromTokenSymbol}
                          </span>
                          <LiveDataBadge isLive={true} variant="small" />
                        </div>
                      ) : (
                        <span className="text-gray-500 text-sm">—</span>
                      )}
                    </div>
                  </div>
                )}

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
                      per {fromTokenSymbol}
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
                totalTakes={takes.length}
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
            <InternalLink
              to={`/auction/${chainId}/${auctionAddress}`}
              variant="default"
              className="block w-full p-3 text-center bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
              showArrow={false}
            >
              <div className="text-sm font-medium text-gray-200">View Auction</div>
              <div className="text-xs text-gray-500">See all rounds</div>
            </InternalLink>
            
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
          hideAuctionColumn={true}
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
