import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Clock,
  DollarSign,
  TrendingDown,
  TrendingUp,
  Users,
  ExternalLink,
  Copy,
  Check,
  Activity,
  Zap
} from 'lucide-react'
import { apiClient, AuctionWebSocket } from '../lib/api'
import type { PriceData } from '../types/auction'
import ActivityTable from '../components/ActivityTable'
import StatsCard from '../components/StatsCard'
import LoadingSpinner from '../components/LoadingSpinner'
import {
  formatAddress,
  formatTokenAmount,
  formatUSD,
  formatTimeAgo,
  formatDuration,
  getAuctionProgress,
  getAuctionStatus,
  copyToClipboard,
  getAddressLink,
  cn
} from '../lib/utils'

const AuctionDetails: React.FC = () => {
  const { address } = useParams<{ address: string }>()
  const [realtimePrice, setRealtimePrice] = useState<PriceData | null>(null)
  const [wsConnection, setWsConnection] = useState<AuctionWebSocket | null>(null)
  const [copiedAddresses, setCopiedAddresses] = useState<Set<string>>(new Set())

  // Fetch auction details
  const { data: auction, isLoading, error } = useQuery({
    queryKey: ['auction', address],
    queryFn: () => apiClient.getAuction(address!),
    enabled: !!address
  })

  // Fetch auction activity
  const { data: activity } = useQuery({
    queryKey: ['auctionActivity', address],
    queryFn: () => apiClient.getAuctionActivity(address!, 50),
    enabled: !!address
  })

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!address) return

    const ws = new AuctionWebSocket(
      address,
      (data) => {
        if (data.type === 'price_update') {
          setRealtimePrice(data.price)
        }
      },
      (error) => {
        console.error('WebSocket error:', error)
      }
    )

    ws.connect()
    setWsConnection(ws)

    return () => {
      ws.disconnect()
      setWsConnection(null)
    }
  }, [address])

  const handleCopy = async (text: string) => {
    const success = await copyToClipboard(text)
    if (success) {
      setCopiedAddresses(prev => new Set(prev).add(text))
      // Reset the copied state after 800ms
      setTimeout(() => {
        setCopiedAddresses(prev => {
          const newSet = new Set(prev)
          newSet.delete(text)
          return newSet
        })
      }, 800)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (error || !auction) {
    return (
      <div className="space-y-8">
        <div className="flex items-center space-x-4">
          <Link
            to="/"
            className="btn btn-secondary btn-sm"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>
        </div>

        <div className="card text-center py-12">
          <h2 className="text-xl font-semibold text-gray-300 mb-2">
            Auction Not Found
          </h2>
          <p className="text-gray-500">
            The auction at {formatAddress(address || '', 10)} could not be loaded.
          </p>
        </div>
      </div>
    )
  }

  // Calculate auction progress and status
  const kickEvents = activity?.filter(event => event.event_type === 'kick') || []
  const takeEvents = activity?.filter(event => event.event_type === 'take') || []
  const latestKick = kickEvents[0]
  
  let progress = 0
  let status = 'inactive'
  let timeRemaining = 0

  if (latestKick) {
    progress = getAuctionProgress(latestKick.timestamp, auction.auction_length)
    status = getAuctionStatus(progress)
    timeRemaining = Math.max(0, auction.auction_length - (Date.now() / 1000 - latestKick.timestamp))
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/"
            className="btn btn-secondary btn-sm"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>
          
          <div>
            <h1 className="text-2xl font-bold text-gray-100">
              Auction Details
            </h1>
            <div className="flex items-center space-x-2 mt-1">
              <button
                onClick={() => handleCopy(auction.address)}
                className="font-mono text-sm text-gray-400 hover:text-gray-200 flex items-center space-x-1 transition-colors"
              >
                <span>{formatAddress(auction.address, 12)}</span>
                {copiedAddresses.has(auction.address) ? (
                  <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
              
              <a
                href={getAddressLink(auction.address)}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className={cn(
            "badge",
            status === 'active' ? 'badge-success' :
            status === 'ending' ? 'badge-warning' :
            'badge-neutral'
          )}>
            {status}
          </div>
          
          {wsConnection && (
            <div className="flex items-center space-x-2 text-sm">
              <div className="h-2 w-2 bg-success-500 rounded-full animate-pulse"></div>
              <span className="text-gray-400">Live</span>
            </div>
          )}
        </div>
      </div>

      {/* Progress bar for active auctions */}
      {status === 'active' && progress > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold">Auction Progress</h3>
            <span className="text-sm text-gray-400">{progress.toFixed(1)}% complete</span>
          </div>
          
          <div className="space-y-3">
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-primary-500 to-primary-400 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            
            <div className="flex items-center justify-between text-sm text-gray-400">
              <span>Started {latestKick && formatTimeAgo(latestKick.timestamp)}</span>
              <span>
                {timeRemaining > 0 
                  ? `${formatDuration(Math.floor(timeRemaining))} remaining`
                  : 'Auction ended'
                }
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Key Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Kicks"
          value={auction.total_kicks}
          icon={TrendingUp}
          iconColor="text-primary-500"
        />
        
        <StatsCard
          title="Total Takes"
          value={auction.total_takes}
          icon={TrendingDown}
          iconColor="text-primary-500"
        />
        
        <StatsCard
          title="Total Volume"
          value={formatUSD(auction.total_volume)}
          icon={DollarSign}
          iconColor="text-yellow-500"
        />
        
        <StatsCard
          title="Status"
          value={auction.current_round?.is_active ? 'Active' : 'Inactive'}
          icon={Activity}
          iconColor={auction.current_round?.is_active ? "text-primary-500" : "text-gray-500"}
        />
      </div>

      {/* Auction Configuration */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Configuration</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div>
            <div className="text-sm text-gray-500 mb-1">Want Token</div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-sm">
                {auction.want_token.symbol}
              </span>
              <button
                onClick={() => handleCopy(auction.want_token.address)}
                className="text-gray-400 hover:text-gray-200"
              >
                {copiedAddresses.has(auction.want_token.address) ? (
                  <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </div>
            <div className="text-xs text-gray-600 font-mono">
              {formatAddress(auction.want_token.address)}
            </div>
          </div>
          
          <div>
            <div className="text-sm text-gray-500 mb-1">Auction Length</div>
            <div className="font-medium">
              {formatDuration(auction.auction_length)}
            </div>
          </div>
          
          <div>
            <div className="text-sm text-gray-500 mb-1">Update Interval</div>
            <div className="font-medium">
              {auction.price_update_interval}s
            </div>
          </div>
          
          <div>
            <div className="text-sm text-gray-500 mb-1">Starting Price</div>
            <div className="font-mono text-sm">
              {formatTokenAmount(auction.starting_price, 18, 6)}
            </div>
          </div>
          
          <div>
            <div className="text-sm text-gray-500 mb-1">Step Decay</div>
            <div className="font-mono text-xs">
              {formatTokenAmount(auction.step_decay, 27, 8)}
            </div>
          </div>

          {realtimePrice && (
            <div>
              <div className="text-sm text-gray-500 mb-1 flex items-center space-x-1">
                <Zap className="h-3 w-3" />
                <span>Current Price</span>
              </div>
              <div className="font-mono text-sm text-primary-400">
                {formatTokenAmount(realtimePrice.price, 18, 6)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Enabled Tokens */}
      {auction.enabled_tokens && auction.enabled_tokens.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">
            Enabled Tokens ({auction.enabled_tokens.length})
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {auction.enabled_tokens.map((token) => (
              <div
                key={token.address}
                className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
              >
                <div>
                  <div className="font-medium">{token.symbol}</div>
                  <div className="text-sm text-gray-500 font-mono">
                    {formatAddress(token.address, 8)}
                  </div>
                </div>
                
                <button
                  onClick={() => handleCopy(token.address)}
                  className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors"
                >
                  {copiedAddresses.has(token.address) ? (
                    <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activity History */}
      {activity && activity.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-lg font-semibold">Activity History</h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ActivityTable
              events={kickEvents.slice(0, 10)}
              title="Kick Events"
              type="kick"
              maxHeight="max-h-96"
            />
            
            <ActivityTable
              events={takeEvents.slice(0, 10)}
              title="Take Events"
              type="take"
              maxHeight="max-h-96"
            />
          </div>
          
          {activity.length > 20 && (
            <div className="text-center">
              <span className="text-sm text-gray-500">
                Showing latest 20 events of {activity.length} total
              </span>
            </div>
          )}
        </div>
      )}

      {/* No Activity State */}
      {(!activity || activity.length === 0) && (
        <div className="card text-center py-8">
          <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
            <Users className="h-6 w-6 text-gray-600" />
          </div>
          <h4 className="text-lg font-medium text-gray-400 mb-1">No Activity Yet</h4>
          <p className="text-sm text-gray-600">
            This auction hasn't been kicked or taken from yet.
          </p>
        </div>
      )}
    </div>
  )
}

export default AuctionDetails