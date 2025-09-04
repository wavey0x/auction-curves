import React, { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Trophy,
  TrendingUp, 
  DollarSign,
  Activity,
  Target,
  Clock,
  AlertCircle,
  User
} from 'lucide-react'
import { apiClient } from '../lib/api'
import StatsCard from '../components/StatsCard'
import LoadingSpinner from '../components/LoadingSpinner'
import AddressDisplay from '../components/AddressDisplay'
import BackButton from '../components/BackButton'
import InternalLink from '../components/InternalLink'
import ChainIcon from '../components/ChainIcon'
import TokenPairDisplay from '../components/TokenPairDisplay'
import { formatAddress, formatUSD, formatNumber, formatTimeAgo, getTxLink } from '../lib/utils'
import Pagination from '../components/Pagination'

const TakerDetails: React.FC = () => {
  const { address } = useParams<{ address: string }>()
  const [takesPage, setTakesPage] = useState(1)
  const [chainFilter] = useState<number | undefined>()
  const [rankingMode, setRankingMode] = useState<'takes' | 'volume'>('takes')
  const [tokenPairsPage, setTokenPairsPage] = useState(1)
  const takesLimit = 10
  const tokenPairsLimit = 10

  // Fetch taker details
  const { data: takerDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['taker', address],
    queryFn: () => apiClient.getTakerDetails(address!),
    enabled: !!address
  })

  // Fetch taker takes with pagination
  const { data: takesResponse, isLoading: takesLoading } = useQuery({
    queryKey: ['takerTakes', address, takesPage, chainFilter],
    queryFn: () => apiClient.getTakerTakes(address!, { 
      page: takesPage, 
      limit: takesLimit,
      chain_id: chainFilter 
    }),
    enabled: !!address
  })

  // Fetch taker token pairs with pagination
  const { data: tokenPairsResponse, isLoading: tokenPairsLoading } = useQuery({
    queryKey: ['takerTokenPairs', address, tokenPairsPage],
    queryFn: () => apiClient.getTakerTokenPairs(address!, { 
      page: tokenPairsPage, 
      limit: tokenPairsLimit 
    }),
    enabled: !!address
  })

  const isLoading = detailsLoading || takesLoading

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (!takerDetails) {
    return (
      <div className="card text-center py-12">
        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="h-8 w-8 text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-400 mb-2">Taker Not Found</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          The requested taker could not be found.
        </p>
        <div className="mt-4">
          <BackButton />
        </div>
      </div>
    )
  }

  const takes = takesResponse?.takes || []
  const uniqueChains = new Set(takerDetails.auction_breakdown.map(ab => ab.chain_id))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <BackButton />
          <div className="flex items-center space-x-3">
            <User className="h-8 w-8 text-primary-400" />
            <h1 className="text-2xl font-bold text-gray-100">Taker Details</h1>
          </div>
        </div>
      </div>

      {/* Taker Overview Card */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-3">
          <Trophy className="h-5 w-5 text-yellow-400" />
          <span>Taker Overview</span>
        </h3>
        
        <div className="border-b border-gray-800 mb-6"></div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <span className="text-sm text-gray-500">Address</span>
              <div className="font-mono text-sm text-white">
                <AddressDisplay address={address!} />
              </div>
            </div>
            
            <div>
              <span className="text-sm text-gray-500">Ranking</span>
              <div 
                className="flex items-center space-x-2 cursor-pointer hover:bg-gray-800/50 rounded p-2 -m-2 transition-colors"
                onClick={() => setRankingMode(rankingMode === 'takes' ? 'volume' : 'takes')}
                title="Click to toggle between takes and volume ranking"
              >
                <Trophy className="h-4 w-4 text-yellow-400" />
                <span className="text-yellow-400 font-bold">
                  #{rankingMode === 'takes' ? takerDetails.rank_by_takes : (takerDetails.rank_by_volume || '—')}
                </span>
                <span className="text-sm text-gray-400">
                  {rankingMode === 'takes' ? 'by takes' : 'by USD'}
                </span>
              </div>
            </div>

          </div>

          <div className="space-y-4">
            <div>
              <span className="text-sm text-gray-500">Unique Chains</span>
              <div className="flex items-center space-x-2 mt-1">
                {Array.from(uniqueChains).map(chainId => (
                  <ChainIcon key={chainId} chainId={chainId} size="sm" />
                ))}
                <span className="text-gray-300 ml-2">({uniqueChains.size} chains)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Activity Period Badges */}
        <div className="flex items-center justify-center space-x-4 pt-6 mt-6 border-t border-gray-800">
          {takerDetails.first_take && (
            <div className="flex items-center space-x-2 px-3 py-2 bg-gray-800 rounded-lg">
              <Clock className="h-4 w-4 text-blue-400" />
              <span className="text-sm text-gray-300">
                <span className="text-gray-500">First seen:</span>{' '}
                <span className="font-medium">{formatTimeAgo(takerDetails.first_take)}</span>
              </span>
            </div>
          )}
          
          {takerDetails.last_take && (
            <div className="flex items-center space-x-2 px-3 py-2 bg-gray-800 rounded-lg">
              <Clock className="h-4 w-4 text-green-400" />
              <span className="text-sm text-gray-300">
                <span className="text-gray-500">Last seen:</span>{' '}
                <span className="font-medium">{formatTimeAgo(takerDetails.last_take)}</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Takes"
          value={formatNumber(takerDetails.total_takes)}
          icon={TrendingUp}
          iconColor="text-green-400"
        />
        
        <StatsCard
          title="Total Volume"
          value={takerDetails.total_volume_usd !== null ? formatUSD(takerDetails.total_volume_usd) : '—'}
          icon={DollarSign}
          iconColor="text-green-400"
        />
        
        <StatsCard
          title="Unique Auctions"
          value={formatNumber(takerDetails.unique_auctions)}
          icon={Target}
          iconColor="text-blue-400"
        />
        
        <StatsCard
          title="Avg Take Value"
          value={takerDetails.avg_take_size_usd !== null ? formatUSD(takerDetails.avg_take_size_usd) : '—'}
          icon={Activity}
          iconColor="text-purple-400"
        />
      </div>

      {/* Recent Takes */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center space-x-3">
            <Clock className="h-5 w-5 text-blue-400" />
            <span>Recent Takes</span>
            {takesResponse && (
              <span className="text-sm text-gray-500">
                ({takesResponse.total_count} total)
              </span>
            )}
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="table">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-left px-4 py-3">Chain</th>
                <th className="text-left px-4 py-3">Auction</th>
                <th className="text-left px-4 py-3">Round</th>
                <th className="text-left px-4 py-3">Tokens</th>
                <th className="text-center px-4 py-3">Value</th>
                <th className="text-left px-4 py-3">Taker P&L</th>
                <th className="text-left px-4 py-3">Time</th>
                <th className="text-left px-4 py-3">Tx</th>
              </tr>
            </thead>
            <tbody className="bg-gray-900">
              {takes.map((take) => (
                <tr key={take.take_id} className="group hover:bg-gray-800/50">
                  <td className="px-4 py-3">
                    <ChainIcon chainId={take.chain_id} size="sm" />
                  </td>
                  <td className="px-4 py-3">
                    <InternalLink
                      to={`/auction/${take.chain_id}/${take.auction}`}
                      variant="address"
                      address={take.auction}
                      chainId={take.chain_id}
                      className="font-mono text-sm"
                    >
                      {formatAddress(take.auction)}
                    </InternalLink>
                  </td>
                  <td className="px-4 py-3">
                    <InternalLink
                      to={`/round/${take.chain_id}/${take.auction}/${take.round_id}`}
                      variant="round"
                    >
                      R{take.round_id}
                    </InternalLink>
                  </td>
                  <td className="px-4 py-3">
                    {/* Tokens column using standard TokenPairDisplay - left aligned */}
                    <TokenPairDisplay
                      fromToken={(take as any).from_token_symbol || 'FROM'}
                      toToken={(take as any).to_token_symbol || 'TO'}
                      size="sm"
                    />
                  </td>
                  <td className="px-4 py-3">
                    {/* Value column combining amount and price */}
                    <div className="text-sm">
                      <div className="font-bold text-gray-100 leading-tight">
                        {take.price_usd !== null ? formatUSD(take.price_usd) : '—'}
                      </div>
                      <div className="text-xs text-gray-400 leading-tight mt-0.5">
                        {/* Show amount taken from the available data - max 3 decimals */}
                        {(take as any).amount_taken ? (
                          `${parseFloat((take as any).amount_taken).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 3 })} ${(take as any).from_token_symbol || 'tokens'}`
                        ) : (
                          `${parseFloat(take.sold).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 3 })} tokens`
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {/* Restore P&L calculation using dynamic properties */}
                    {(take as any).amount_taken_usd && (take as any).amount_paid_usd ? (() => {
                      const takerPnL = parseFloat((take as any).amount_taken_usd) - parseFloat((take as any).amount_paid_usd);
                      const isProfit = takerPnL >= 0;
                      return (
                        <div className="text-sm text-center">
                          <div className={`font-medium leading-tight ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                            {formatUSD(Math.abs(takerPnL), 2)}
                          </div>
                          <div className={`text-xs leading-tight font-medium ${isProfit ? 'text-green-500' : 'text-red-500'}`}>
                            {isProfit ? '+' : '-'}{((Math.abs(takerPnL) / parseFloat((take as any).amount_paid_usd)) * 100).toFixed(2)}%
                          </div>
                        </div>
                      );
                    })() : (
                      <div className="text-xs text-gray-500 text-center">
                        N/A
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-400">
                      {formatTimeAgo(take.timestamp)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <a 
                      href={getTxLink(take.tx_hash, take.chain_id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-sm text-white hover:text-primary-300 transition-colors"
                    >
                      {formatAddress(take.tx_hash)}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {takesResponse && takesResponse.total_pages > 1 && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <Pagination
              currentPage={takesPage}
              canGoPrev={takesPage > 1}
              canGoNext={takesPage < takesResponse.total_pages}
              onPrev={() => setTakesPage(p => Math.max(1, p - 1))}
              onNext={() => setTakesPage(p => Math.min(takesResponse.total_pages, p + 1))}
              totalPages={takesResponse.total_pages}
              summaryText={`${takesResponse.total_count} total takes`}
            />
          </div>
        )}
      </div>

      {/* Token Pairs */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center space-x-3">
            <Target className="h-5 w-5 text-blue-400" />
            <span>Most Frequent Token Pairs</span>
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="table">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-left px-4 py-3">Chains</th>
                <th className="text-left px-4 py-3">From Token</th>
                <th className="text-left px-4 py-3">To Token</th>
                <th className="text-left px-4 py-3">Takes Count</th>
                <th className="text-left px-4 py-3">Volume</th>
                <th className="text-left px-4 py-3">Last Take</th>
              </tr>
            </thead>
            <tbody className="bg-gray-900">
              {tokenPairsResponse?.token_pairs?.map((tokenPair, index) => (
                <tr key={`${tokenPair.from_token}-${tokenPair.to_token}`} className="group hover:bg-gray-800/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-1">
                      {tokenPair.active_chains?.slice(0, 3).map(chainId => (
                        <ChainIcon key={chainId} chainId={chainId} size="sm" />
                      ))}
                      {tokenPair.active_chains?.length > 3 && (
                        <span className="text-xs text-gray-500">+{tokenPair.active_chains.length - 3}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-white">
                        {tokenPair.from_token_symbol || 'Unknown'}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">
                        {formatAddress(tokenPair.from_token)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                      <span className="font-medium text-white">
                        {tokenPair.to_token_symbol || 'Unknown'}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">
                        {formatAddress(tokenPair.to_token)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-green-400">
                      {formatNumber(tokenPair.takes_count)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium">
                      {tokenPair.volume_usd !== null ? formatUSD(tokenPair.volume_usd) : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-400">
                      {tokenPair.last_take ? formatTimeAgo(tokenPair.last_take) : '—'}
                    </span>
                  </td>
                </tr>
              ))}
              {(!tokenPairsResponse?.token_pairs || tokenPairsResponse.token_pairs.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                    No token pairs found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Token Pairs Pagination */}
        {tokenPairsResponse && tokenPairsResponse.total_pages > 1 && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <Pagination
              currentPage={tokenPairsPage}
              canGoPrev={tokenPairsPage > 1}
              canGoNext={tokenPairsPage < tokenPairsResponse.total_pages}
              onPrev={() => setTokenPairsPage(p => Math.max(1, p - 1))}
              onNext={() => setTokenPairsPage(p => Math.min(tokenPairsResponse.total_pages, p + 1))}
              totalPages={tokenPairsResponse.total_pages}
              summaryText={`${tokenPairsResponse.total_count} total token pairs`}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default TakerDetails