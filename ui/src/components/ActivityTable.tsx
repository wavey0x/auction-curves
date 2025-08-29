import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, Copy, TrendingDown, TrendingUp, Check } from 'lucide-react'
import type { ActivityEvent } from '../types/auction'
import {
  formatAddress,
  formatTokenAmount,
  formatUSD,
  formatTimeAgo,
  getTxLink,
  getChainInfo,
  copyToClipboard,
  cn
} from '../lib/utils'

interface ActivityTableProps {
  events: ActivityEvent[]
  title: string
  type?: 'kick' | 'take' | 'all'
  maxHeight?: string
  tokens?: Array<{address: string, symbol: string, name: string, decimals: number}>
}

const ActivityTable: React.FC<ActivityTableProps> = ({
  events,
  title,
  type = 'all',
  maxHeight = 'max-h-96',
  tokens = []
}) => {
  const [copiedAddresses, setCopiedAddresses] = useState<Set<string>>(new Set())

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

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'kick':
        return <TrendingUp className="h-4 w-4 text-primary-500" />
      case 'take':
        return <TrendingDown className="h-4 w-4 text-primary-500" />
      default:
        return null
    }
  }

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'kick':
        return 'text-success-400'
      case 'take':
        return 'text-primary-400'
      default:
        return 'text-gray-400'
    }
  }

  const chainInfo = getChainInfo(31337) // Using Anvil chain

  if (events.length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center py-8 text-gray-500">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            {type === 'kick' ? (
              <TrendingUp className="h-8 w-8 text-gray-600" />
            ) : type === 'take' ? (
              <TrendingDown className="h-8 w-8 text-gray-600" />
            ) : (
              <div className="h-8 w-8 bg-gray-600 rounded"></div>
            )}
          </div>
          <p className="text-lg font-medium text-gray-400">No {type} events yet</p>
          <p className="text-sm text-gray-600">Events will appear here when auctions become active</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center space-x-2">
          <span>{title}</span>
          <span className="badge badge-neutral">{events.length}</span>
        </h3>
      </div>

      <div className={cn("overflow-hidden rounded-lg border border-gray-800", maxHeight)}>
        <div className="overflow-y-auto">
          <table className="table">
            <thead className="bg-gray-800/50 sticky top-0">
              <tr>
                <th className="text-center">Event</th>
                <th className="text-center">Auction</th>
                <th className="text-center">Tokens</th>
                <th className="text-center">Amount</th>
                <th className="text-center">Price</th>
                <th className="text-center">Participant</th>
                <th className="text-center">Time</th>
                <th className="text-center w-16">Chain</th>
                <th className="text-center">Tx</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={`${event.tx_hash}-${event.id}`} className="group">
                  <td>
                    <div className="flex items-center space-x-1.5">
                      {getEventIcon(event.event_type)}
                      <span className={cn("font-medium uppercase text-xs", getEventColor(event.event_type))}>
                        {event.event_type}
                      </span>
                    </div>
                  </td>
                  
                  <td>
                    <Link
                      to={`/auction/${event.auction_address}`}
                      className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors"
                    >
                      {formatAddress(event.auction_address, 8)}
                    </Link>
                  </td>
                  
                  <td>
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-1 text-sm">
                        {(() => {
                          const fromToken = tokens.find(t => t.address.toLowerCase() === event.from_token.toLowerCase())
                          const fromSymbol = fromToken?.symbol || formatAddress(event.from_token, 6)
                          
                          return (
                            <>
                              <span className="font-medium text-gray-300">{fromSymbol}</span>
                              {event.to_token && (() => {
                                const toToken = tokens.find(t => t.address.toLowerCase() === event.to_token!.toLowerCase())
                                const toSymbol = toToken?.symbol || formatAddress(event.to_token, 6)
                                return (
                                  <>
                                    <span className="text-gray-500">→</span>
                                    <span className="font-medium text-gray-300">{toSymbol}</span>
                                  </>
                                )
                              })()}
                            </>
                          )
                        })()}
                      </div>
                    </div>
                  </td>
                  
                  <td>
                    <div className="text-sm">
                      <div className="font-medium text-gray-200 leading-tight">
                        {formatTokenAmount(event.amount, 18, 4)}
                      </div>
                      {event.event_type === 'take' && 'amount_in' in event && (
                        <div className="text-xs text-gray-500 leading-tight">
                          in: {formatTokenAmount((event as any).amount_in, 18, 2)}
                        </div>
                      )}
                    </div>
                  </td>
                  
                  <td>
                    {event.price ? (
                      <div className="text-sm">
                        <div className="font-medium text-gray-200 leading-tight">
                          {formatTokenAmount(event.price, 18, 6)}
                        </div>
                        <div className="text-xs text-gray-500 leading-tight">
                          {formatUSD(parseFloat(event.price) * 1.5)} {/* Rough USD estimate */}
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-500 text-sm">—</span>
                    )}
                  </td>
                  
                  <td>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleCopy(event.participant)}
                        className="group/copy flex items-center space-x-1 font-mono text-sm text-gray-400 hover:text-gray-200 transition-colors"
                        title="Copy address"
                      >
                        <span>{formatAddress(event.participant)}</span>
                        {copiedAddresses.has(event.participant) ? (
                          <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                        ) : (
                          <Copy className="h-3 w-3 opacity-0 group-hover/copy:opacity-100 transition-opacity" />
                        )}
                      </button>
                    </div>
                  </td>
                  
                  <td>
                    <span className="text-sm text-gray-400" title={new Date(event.timestamp * 1000).toLocaleString()}>
                      {formatTimeAgo(event.timestamp)}
                    </span>
                  </td>
                  
                  <td>
                    <div className="flex items-center space-x-1">
                      <span className="text-lg" title={chainInfo.name}>
                        {chainInfo.logo}
                      </span>
                    </div>
                  </td>
                  
                  <td>
                    <div className="flex items-center space-x-2">
                      {chainInfo.explorer !== '#' ? (
                        <a
                          href={getTxLink(event.tx_hash, 31337)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
                          title="View transaction"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <button
                          onClick={() => handleCopy(event.tx_hash)}
                          className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
                          title="Copy transaction hash"
                        >
                          {copiedAddresses.has(event.tx_hash) ? (
                            <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default ActivityTable