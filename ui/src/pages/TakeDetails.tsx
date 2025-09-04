import React from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Activity,
  DollarSign,
  Fuel,
  TrendingUp,
  Clock,
  AlertCircle,
  Hash,
  Zap,
  Target
} from 'lucide-react'
import { apiClient } from '../lib/api'
import StatsCard from '../components/StatsCard'
import LoadingSpinner from '../components/LoadingSpinner'
import BackButton from '../components/BackButton'
import ChainIcon from '../components/ChainIcon'
import CollapsibleSection from '../components/CollapsibleSection'
import KeyValueGrid from '../components/KeyValueGrid'
import PriceComparisonTable from '../components/PriceComparisonTable'
import TokenPairDisplay from '../components/TokenPairDisplay'
import TakerLink from '../components/TakerLink'
import InternalLink from '../components/InternalLink'
import StandardTxHashLink from '../components/StandardTxHashLink'
import AddressDisplay from '../components/AddressDisplay'
import { 
  formatUSD, 
  formatReadableTokenAmount,
  formatTimeAgo 
} from '../lib/utils'

const TakeDetails: React.FC = () => {
  const { chainId, auctionAddress, roundId, takeSeq } = useParams<{
    chainId: string
    auctionAddress: string
    roundId: string
    takeSeq: string
  }>()

  const { data: takeDetails, isLoading, error } = useQuery({
    queryKey: ['takeDetails', chainId, auctionAddress, roundId, takeSeq],
    queryFn: () => apiClient.getTakeDetails(parseInt(chainId!), auctionAddress!, parseInt(roundId!), parseInt(takeSeq!)),
    enabled: !!chainId && !!auctionAddress && !!roundId && !!takeSeq,
    refetchInterval: 5 * 60 * 1000 // Refetch every 5 minutes
  })

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    )
  }

  if (error || !takeDetails) {
    return (
      <div className="card text-center py-12">
        <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="h-8 w-8 text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-400 mb-2">Take Not Found</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          The requested take details could not be found or loaded.
        </p>
        <div className="mt-4">
          <BackButton />
        </div>
      </div>
    )
  }

  // Group price quotes by token
  const fromTokenQuotes = takeDetails.price_quotes.filter(
    q => q.token_address.toLowerCase() === takeDetails.from_token.toLowerCase()
  )
  const toTokenQuotes = takeDetails.price_quotes.filter(
    q => q.token_address.toLowerCase() === takeDetails.to_token.toLowerCase()
  )

  const hasGasData = takeDetails.gas_used || takeDetails.transaction_fee_eth

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <BackButton />
          <div className="flex items-center space-x-3">
            <ChainIcon chainId={takeDetails.chain_id} size="sm" showName={false} />
            <div>
              <h1 className="text-2xl font-bold text-gray-100">Take Details</h1>
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                <span className="font-mono">{takeDetails.take_id}</span>
                <span>•</span>
                <span>Take #{takeDetails.take_seq} in Round {takeDetails.round_id}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Take Value"
          value={formatUSD(takeDetails.pnl_analysis.take_value_usd)}
          icon={DollarSign}
          iconColor="text-blue-400"
        />
        
        {hasGasData && (
          <StatsCard
            title="Gas Cost"
            value={takeDetails.transaction_fee_usd 
              ? formatUSD(takeDetails.transaction_fee_usd)
              : `${takeDetails.transaction_fee_eth?.toFixed(6)} ETH`
            }
            icon={Fuel}
            iconColor="text-orange-400"
          />
        )}
        
        <StatsCard
          title="PnL Range"
          value={`${formatUSD(takeDetails.pnl_analysis.worst_case_pnl)} to ${formatUSD(takeDetails.pnl_analysis.best_case_pnl)}`}
          icon={TrendingUp}
          iconColor={takeDetails.pnl_analysis.base_pnl >= 0 ? "text-green-400" : "text-red-400"}
        />
        
        <StatsCard
          title="Time Ago"
          value={formatTimeAgo(new Date(takeDetails.timestamp).getTime() / 1000)}
          icon={Clock}
          iconColor="text-purple-400"
        />
      </div>

      {/* Core Information */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Transaction Details</h3>
        <KeyValueGrid items={[
          { label: "Transaction Hash", value: <StandardTxHashLink txHash={takeDetails.tx_hash} chainId={takeDetails.chain_id} /> },
          { label: "Block Number", value: <span className="font-mono">#{takeDetails.block_number.toLocaleString()}</span> },
          { label: "Timestamp", value: new Date(takeDetails.timestamp).toLocaleString() },
          { label: "Taker", value: <TakerLink takerAddress={takeDetails.taker} chainId={takeDetails.chain_id} /> },
          { label: "Auction", value: <InternalLink to={`/auction/${takeDetails.chain_id}/${takeDetails.auction_address}`} variant="address">{takeDetails.auction_address}</InternalLink> },
          { label: "Round", value: <InternalLink to={`/round/${takeDetails.chain_id}/${takeDetails.auction_address}/${takeDetails.round_id}`} variant="round">R{takeDetails.round_id}</InternalLink> },
          { label: "Take Sequence", value: `Take ${takeDetails.take_seq}${takeDetails.round_total_takes ? ` of ${takeDetails.round_total_takes}` : ''}` }
        ]} />
      </div>

      {/* Token Exchange Details */}
      <CollapsibleSection title="Token Exchange" defaultOpen={true}>
        <div className="space-y-6">
          {/* Token Pair Display */}
          <div className="flex items-center justify-center">
            <TokenPairDisplay 
              fromToken={takeDetails.from_token_symbol || 'FROM'}
              toToken={takeDetails.to_token_symbol || 'TO'}
            />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* From Token */}
            <div className="card bg-gray-800/50">
              <h4 className="font-semibold mb-3 text-primary-400">Tokens Received</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Amount:</span>
                  <span className="font-mono">{formatReadableTokenAmount(takeDetails.amount_taken)} {takeDetails.from_token_symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Token:</span>
                  <AddressDisplay address={takeDetails.from_token} />
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">USD Value:</span>
                  <span className="font-mono">{formatUSD(takeDetails.pnl_analysis.take_value_usd)}</span>
                </div>
              </div>
            </div>

            {/* To Token */}
            <div className="card bg-gray-800/50">
              <h4 className="font-semibold mb-3 text-orange-400">Tokens Paid</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Amount:</span>
                  <span className="font-mono">{formatReadableTokenAmount(takeDetails.amount_paid)} {takeDetails.to_token_symbol}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Token:</span>
                  <AddressDisplay address={takeDetails.to_token} />
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Exchange Rate:</span>
                  <span className="font-mono">{formatReadableTokenAmount(takeDetails.price)} {takeDetails.to_token_symbol}/{takeDetails.from_token_symbol}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CollapsibleSection>

      {/* Price Comparison Table */}
      {(fromTokenQuotes.length > 0 && toTokenQuotes.length > 0) && (
        <PriceComparisonTable
          fromTokenQuotes={fromTokenQuotes}
          toTokenQuotes={toTokenQuotes}
          amountTaken={parseFloat(takeDetails.amount_taken)}
          amountPaid={parseFloat(takeDetails.amount_paid)}
          fromTokenSymbol={takeDetails.from_token_symbol || 'FROM'}
          toTokenSymbol={takeDetails.to_token_symbol || 'TO'}
        />
      )}

      {/* Gas Analysis */}
      {hasGasData && (
        <CollapsibleSection title="Gas & Transaction Costs" defaultOpen={true}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {takeDetails.gas_price && (
              <div className="bg-gray-800/50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <Zap className="h-4 w-4 text-yellow-400" />
                  <span className="font-medium">Gas Price</span>
                </div>
                <div className="font-mono text-lg">{takeDetails.gas_price.toFixed(2)} Gwei</div>
              </div>
            )}

            {takeDetails.base_fee && (
              <div className="bg-gray-800/50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <Hash className="h-4 w-4 text-blue-400" />
                  <span className="font-medium">Base Fee</span>
                </div>
                <div className="font-mono text-lg">{takeDetails.base_fee.toFixed(2)} Gwei</div>
                <div className="text-xs text-gray-500">EIP-1559</div>
              </div>
            )}

            {takeDetails.priority_fee && (
              <div className="bg-gray-800/50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <Target className="h-4 w-4 text-green-400" />
                  <span className="font-medium">Priority Fee</span>
                </div>
                <div className="font-mono text-lg">{takeDetails.priority_fee.toFixed(2)} Gwei</div>
                <div className="text-xs text-gray-500">Miner tip</div>
              </div>
            )}

            {takeDetails.gas_used && (
              <div className="bg-gray-800/50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <Activity className="h-4 w-4 text-purple-400" />
                  <span className="font-medium">Gas Used</span>
                </div>
                <div className="font-mono text-lg">{takeDetails.gas_used.toLocaleString()}</div>
              </div>
            )}

            {takeDetails.transaction_fee_eth && (
              <div className="bg-gray-800/50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <Fuel className="h-4 w-4 text-orange-400" />
                  <span className="font-medium">Total Fee</span>
                </div>
                <div className="font-mono text-lg">{takeDetails.transaction_fee_eth.toFixed(6)} ETH</div>
                {takeDetails.transaction_fee_usd && (
                  <div className="text-sm text-gray-400">{formatUSD(takeDetails.transaction_fee_usd)}</div>
                )}
              </div>
            )}

            {takeDetails.pnl_analysis.take_value_usd > 0 && takeDetails.transaction_fee_usd && (
              <div className="bg-gray-800/50 p-4 rounded-lg">
                <div className="flex items-center space-x-2 mb-2">
                  <DollarSign className="h-4 w-4 text-red-400" />
                  <span className="font-medium">Fee %</span>
                </div>
                <div className="font-mono text-lg">
                  {((takeDetails.transaction_fee_usd / takeDetails.pnl_analysis.take_value_usd) * 100).toFixed(3)}%
                </div>
                <div className="text-xs text-gray-500">of take value</div>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Auction Context */}
      <CollapsibleSection title="Auction Context">
        <KeyValueGrid items={[
          ...(takeDetails.auction_decay_rate ? [{ label: "Decay Rate", value: `${(takeDetails.auction_decay_rate * 100).toFixed(3)}% per step` }] : []),
          ...(takeDetails.auction_update_interval ? [{ label: "Update Interval", value: `${takeDetails.auction_update_interval} seconds` }] : []),
          ...(takeDetails.round_total_takes ? [{ label: "Total Takes in Round", value: takeDetails.round_total_takes.toString() }] : []),
          ...(takeDetails.round_available_before ? [{ label: "Available Before Take", value: formatReadableTokenAmount(takeDetails.round_available_before) }] : []),
          ...(takeDetails.round_available_after ? [{ label: "Available After Take", value: formatReadableTokenAmount(takeDetails.round_available_after) }] : []),
        ]} />
      </CollapsibleSection>
    </div>
  )
}

export default TakeDetails