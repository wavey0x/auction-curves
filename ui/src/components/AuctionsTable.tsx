import React, { useState, useMemo, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  ArrowUpDown, 
  ArrowUp, 
  ArrowDown,
  Search,
  TrendingDown,
  ChevronDown,
  Check
} from 'lucide-react'
import type { AuctionListItem } from '../types/auction'
import { formatTimeAgo, formatAddress } from '../lib/utils'
import { apiClient } from '../lib/api'
import ChainIcon from './ChainIcon'
import TokensList from './TokensList'
import AddressLink from './AddressLink'
import InternalLink from './InternalLink'
import TokenPairDisplay from './TokenPairDisplay'
import { useKickableStatus } from '../hooks/useKickableStatus'
import { getChainDisplay } from '../lib/chainData'

// Status configuration with colors and labels
const statusConfig = {
  kickable: {
    label: 'Kickable',
    textColor: 'text-purple-400',
    dotColor: 'bg-purple-500',
    animated: true,
  },
  active: {
    label: 'Active',
    textColor: 'text-success-400',
    dotColor: 'bg-success-500',
    animated: true,
  },
  inactive: {
    label: 'Inactive',
    textColor: 'text-gray-500',
    dotColor: 'bg-gray-600',
    animated: false,
  },
} as const

export type AuctionStatus = 'active' | 'inactive' | 'kickable'

interface AuctionsTableProps {
  auctions: AuctionListItem[]
}

type SortField = 'address' | 'status' | 'decay_rate' | 'update_interval' | 'last_kicked'
type SortDirection = 'asc' | 'desc'

const AuctionsTable: React.FC<AuctionsTableProps> = ({ auctions = [] }) => {
  const [search, setSearch] = useState('')
  const [tokenFilter, setTokenFilter] = useState('')
  const [tokenSearch, setTokenSearch] = useState('')
  const [tokenDropdownOpen, setTokenDropdownOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string[]>([])
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false)
  const [chainFilter, setChainFilter] = useState('')
  const [chainDropdownOpen, setChainDropdownOpen] = useState(false)
  const [sortField, setSortField] = useState<SortField>('last_kicked')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const tokenDropdownRef = useRef<HTMLDivElement>(null)
  const statusDropdownRef = useRef<HTMLDivElement>(null)

  // Fetch kickable status for all auctions (only triggers on auction list changes)
  const { data: kickableData = {} } = useKickableStatus(auctions)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setChainDropdownOpen(false)
      }
      if (tokenDropdownRef.current && !tokenDropdownRef.current.contains(event.target as Node)) {
        setTokenDropdownOpen(false)
      }
      if (statusDropdownRef.current && !statusDropdownRef.current.contains(event.target as Node)) {
        setStatusDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Extract unique values for filters

  const uniqueTokens = useMemo(() => {
    const tokenMap = new Map<string, { symbol?: string, address: string, display: string }>()
    
    auctions?.forEach(ah => {
      ah.from_tokens?.forEach(token => {
        if (token?.address) {
          const key = token.address.toLowerCase()
          const display = token.symbol 
            ? `${token.symbol} (${formatAddress(token.address)})`
            : formatAddress(token.address)
          
          tokenMap.set(key, {
            symbol: token.symbol,
            address: token.address,
            display
          })
        }
      })
      
      if (ah.want_token?.address) {
        const key = ah.want_token.address.toLowerCase()
        const display = ah.want_token.symbol 
          ? `${ah.want_token.symbol} (${formatAddress(ah.want_token.address)})`
          : formatAddress(ah.want_token.address)
        
        tokenMap.set(key, {
          symbol: ah.want_token.symbol,
          address: ah.want_token.address,
          display
        })
      }
    })
    
    return Array.from(tokenMap.values()).sort((a, b) => a.display.localeCompare(b.display))
  }, [auctions])
  
  // Filter tokens based on search
  const filteredTokens = useMemo(() => {
    if (!tokenSearch.trim()) return uniqueTokens
    
    const searchLower = tokenSearch.toLowerCase()
    return uniqueTokens.filter(token => 
      token.display.toLowerCase().includes(searchLower) ||
      token.symbol?.toLowerCase().includes(searchLower) ||
      token.address.toLowerCase().includes(searchLower)
    )
  }, [uniqueTokens, tokenSearch])

  // Fetch chain data from API  
  const { data: chainData } = useQuery({
    queryKey: ['chains'],
    queryFn: () => apiClient.getChains(),
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  })

  const uniqueChains = useMemo(() => {
    const chainIds = new Set<number>()
    auctions?.forEach(ah => {
      chainIds.add(ah.chain_id)
    })
    
    const chains = Array.from(chainIds).map(chainId => {
      const chainInfo = chainData?.chains[chainId]
      return chainInfo ? {
        chainId,
        name: chainInfo.shortName,
        icon: chainInfo.icon
      } : {
        chainId,
        name: `Chain ${chainId}`,
        icon: null
      }
    })
    
    return chains.sort((a, b) => a.name.localeCompare(b.name))
  }, [auctions, chainData])

  // Filter and sort data
  const filteredAndSorted = useMemo(() => {
    let filtered = (auctions || []).filter(ah => {
      // Search filter
      if (search) {
        const searchLower = search.toLowerCase()
        const matchesAddress = ah.address?.toLowerCase().includes(searchLower)
        const matchesFromTokens = ah.from_tokens?.some(token => 
          token.symbol?.toLowerCase().includes(searchLower) ||
          token.address?.toLowerCase().includes(searchLower)
        ) || false
        const matchesWantToken = 
          ah.want_token?.symbol?.toLowerCase().includes(searchLower) ||
          ah.want_token?.address?.toLowerCase().includes(searchLower)
        
        if (!matchesAddress && !matchesFromTokens && !matchesWantToken) {
          return false
        }
      }

      // Token filter
      if (tokenFilter) {
        const filterAddress = tokenFilter.toLowerCase()
        const hasFromToken = ah.from_tokens?.some(token =>
          token.address?.toLowerCase() === filterAddress
        ) || false
        const hasWantToken = ah.want_token?.address?.toLowerCase() === filterAddress || false
        
        if (!hasFromToken && !hasWantToken) {
          return false
        }
      }


      // Status filter
      if (statusFilter.length > 0) {
        const isActive = ah.current_round?.is_active || false
        const isKickable = kickableData[ah.address]?.isKickable || false
        
        let matchesStatus = false
        
        for (const filter of statusFilter) {
          if (filter === 'active' && isActive) {
            matchesStatus = true
            break
          }
          if (filter === 'inactive' && !isActive) {
            matchesStatus = true
            break
          }
          if (filter === 'kickable' && isKickable) {
            matchesStatus = true
            break
          }
        }
        
        if (!matchesStatus) {
          return false
        }
      }

      // Chain filter
      if (chainFilter) {
        const chainInfo = getChainDisplay(ah.chain_id)
        if (!chainInfo || !chainInfo.shortName.toLowerCase().includes(chainFilter.toLowerCase())) {
          return false
        }
      }

      return true
    })

    // Sort
    filtered.sort((a, b) => {
      let aVal: any
      let bVal: any

      switch (sortField) {
        case 'address':
          aVal = a.address.toLowerCase()
          bVal = b.address.toLowerCase()
          break
        case 'status':
          // Priority: kickable + active (3) > kickable (2) > active (1) > inactive (0)
          const aIsActive = a.current_round?.is_active || false
          const aIsKickable = kickableData[a.address]?.isKickable || false
          const bIsActive = b.current_round?.is_active || false
          const bIsKickable = kickableData[b.address]?.isKickable || false
          
          aVal = (aIsKickable && aIsActive) ? 3 : aIsKickable ? 2 : aIsActive ? 1 : 0
          bVal = (bIsKickable && bIsActive) ? 3 : bIsKickable ? 2 : bIsActive ? 1 : 0
          break
        case 'decay_rate':
          aVal = a.decay_rate
          bVal = b.decay_rate
          break
        case 'update_interval':
          aVal = a.update_interval
          bVal = b.update_interval
          break
        case 'last_kicked':
          aVal = a.last_kicked ? new Date(a.last_kicked).getTime() : 0
          bVal = b.last_kicked ? new Date(b.last_kicked).getTime() : 0
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
      return 0
    })

    return filtered
  }, [auctions, search, tokenFilter, statusFilter, chainFilter, sortField, sortDirection, kickableData])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 text-gray-500" />
    }
    return sortDirection === 'asc' ? 
      <ArrowUp className="h-3 w-3 text-primary-400" /> : 
      <ArrowDown className="h-3 w-3 text-primary-400" />
  }

  return (
    <div className="space-y-4">
      {/* Centered filter group */}
      <div className="flex justify-center">
        <div className="flex flex-wrap gap-2 items-center justify-center max-w-4xl">
          <div className="relative w-full sm:w-60">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search addresses, tokens..."
              className="w-full pl-9 pr-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          <div className="relative w-full sm:w-48" ref={tokenDropdownRef}>
            <div
              className="flex items-center justify-between w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm cursor-pointer focus-within:ring-1 focus-within:ring-primary-500"
              onClick={() => setTokenDropdownOpen(!tokenDropdownOpen)}
            >
              <span className="truncate">
                {tokenFilter 
                  ? uniqueTokens.find(t => t.address.toLowerCase() === tokenFilter.toLowerCase())?.display || 'Unknown Token'
                  : 'All Tokens'
                }
              </span>
              <ChevronDown className={`h-4 w-4 transition-transform ${tokenDropdownOpen ? 'rotate-180' : ''}`} />
            </div>
            
            {tokenDropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg z-50 max-h-64 overflow-hidden">
                <div className="p-2 border-b border-gray-700">
                  <input
                    type="text"
                    placeholder="Search tokens..."
                    className="w-full px-2 py-1 bg-gray-900 border border-gray-600 rounded text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
                    value={tokenSearch}
                    onChange={(e) => setTokenSearch(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
                <div className="max-h-48 overflow-y-auto">
                  <div
                    className="px-2 py-2 text-sm hover:bg-gray-700 cursor-pointer"
                    onClick={() => {
                      setTokenFilter('')
                      setTokenDropdownOpen(false)
                    }}
                  >
                    All Tokens
                  </div>
                  {filteredTokens.map(token => (
                    <div
                      key={token.address}
                      className="px-2 py-2 text-sm hover:bg-gray-700 cursor-pointer truncate"
                      onClick={() => {
                        setTokenFilter(token.address)
                        setTokenDropdownOpen(false)
                      }}
                      title={token.display}
                    >
                      {token.display}
                    </div>
                  ))}
                  {filteredTokens.length === 0 && tokenSearch && (
                    <div className="px-2 py-2 text-sm text-gray-500">
                      No tokens found
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Status Filter Dropdown */}
          <div className="relative w-full sm:w-40" ref={statusDropdownRef}>
            <div
              className="flex items-center justify-between w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm cursor-pointer focus-within:ring-1 focus-within:ring-primary-500"
              onClick={() => setStatusDropdownOpen(!statusDropdownOpen)}
            >
              <span className="truncate">
                {statusFilter.length === 0 
                  ? 'All Status'
                  : statusFilter.length === 1 
                    ? statusConfig[statusFilter[0] as AuctionStatus]?.label || statusFilter[0]
                    : `${statusFilter.length} Selected`
                }
              </span>
              <ChevronDown className={`h-4 w-4 transition-transform ${statusDropdownOpen ? 'rotate-180' : ''}`} />
            </div>
            
            {statusDropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg z-50">
                <div
                  className="px-2 py-2 text-sm hover:bg-gray-700 cursor-pointer flex items-center justify-between"
                  onClick={() => {
                    setStatusFilter([])
                    setStatusDropdownOpen(false)
                  }}
                >
                  <span>All Status</span>
                  {statusFilter.length === 0 && <Check className="h-4 w-4 text-primary-400" />}
                </div>
                
                {(['active', 'kickable', 'inactive'] as const)
                  .map(statusKey => {
                  const config = statusConfig[statusKey]
                  const isSelected = statusFilter.includes(statusKey)
                  return (
                    <div
                      key={statusKey}
                      className="px-2 py-2 text-sm hover:bg-gray-700 cursor-pointer flex items-center justify-between"
                      onClick={() => {
                        if (isSelected) {
                          setStatusFilter(prev => prev.filter(s => s !== statusKey))
                        } else {
                          setStatusFilter(prev => [...prev, statusKey])
                        }
                      }}
                    >
                      <div className="flex items-center space-x-2">
                        <div className={`h-2 w-2 rounded-full ${config.dotColor} ${config.animated ? 'animate-pulse' : ''}`}></div>
                        <span className={config.textColor}>{config.label}</span>
                      </div>
                      {isSelected && <Check className="h-4 w-4 text-primary-400" />}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          
          {/* Custom Chain Filter Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setChainDropdownOpen(!chainDropdownOpen)}
              className="w-full sm:w-36 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 flex items-center justify-between"
            >
              <div className="flex items-center space-x-2">
                {chainFilter ? (
                  <>
                    <ChainIcon 
                      chainId={uniqueChains.find(c => c.name === chainFilter)?.chainId || 0} 
                      size="sm" 
                    />
                    <span>{chainFilter}</span>
                  </>
                ) : (
                  <span>All Chains</span>
                )}
              </div>
              <ChevronDown className={`h-4 w-4 transition-transform ${chainDropdownOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {chainDropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded shadow-lg max-h-48 overflow-y-auto z-50">
                <button
                  onClick={() => {
                    setChainFilter('')
                    setChainDropdownOpen(false)
                  }}
                  className="w-full px-2 py-2 text-left text-sm hover:bg-gray-700 flex items-center space-x-2"
                >
                  <span>All Chains</span>
                </button>
                {uniqueChains.map(chain => (
                  <button
                    key={chain.chainId}
                    onClick={() => {
                      setChainFilter(chain.name)
                      setChainDropdownOpen(false)
                    }}
                    className="w-full px-2 py-2 text-left text-sm hover:bg-gray-700 flex items-center space-x-2"
                  >
                    <ChainIcon chainId={chain.chainId} size="sm" />
                    <span>{chain.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-800">

      {/* Table */}
      <div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-center w-[22px] min-w-[22px] max-w-[22px] px-0"><span className="sr-only">Chain</span></th>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('address')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Address</span>
                    <SortIcon field="address" />
                  </div>
                </th>
                <th className="text-center">Round</th>
                <th className="text-center">Tokens</th>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('status')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Status</span>
                    <SortIcon field="status" />
                  </div>
                </th>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('decay_rate')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Decay Rate</span>
                    <SortIcon field="decay_rate" />
                  </div>
                </th>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('update_interval')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Update Interval</span>
                    <SortIcon field="update_interval" />
                  </div>
                </th>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('last_kicked')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Last Round</span>
                    <SortIcon field="last_kicked" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSorted.map((auction, index) => {
                const isActive = auction.current_round?.is_active || false
                const currentRound = auction.current_round
                
                return (
                  <tr key={`${auction?.address}-${auction?.chain_id}-${auction?.current_round?.round_id || 'no-round'}`} className="group">
                    <td className="w-[22px] min-w-[22px] max-w-[22px] px-0 text-center">
                      <div className="flex justify-center">
                        <ChainIcon 
                          chainId={auction?.chain_id || 31337} 
                          size="xs"
                          showName={false}
                        />
                      </div>
                    </td>
                    <td>
                      <AddressLink
                        address={auction?.address || ''}
                        chainId={auction?.chain_id || 1}
                        type="auction"
                        className="text-primary-400"
                      />
                    </td>
                    
                    <td>
                      {currentRound ? (
                        <InternalLink
                          to={`/round/${auction?.chain_id}/${auction?.address}/${currentRound?.round_id}`}
                          variant="round"
                        >
                          R{currentRound.round_id}
                        </InternalLink>
                      ) : (
                        <span className="text-gray-500 text-sm">—</span>
                      )}
                    </td>
                    
                    <td>
                      <TokenPairDisplay
                        fromToken={
                          <TokensList 
                            tokens={auction.from_tokens || []}
                            maxDisplay={2}
                            tokenClassName="text-gray-300 font-medium"
                          />
                        }
                        toToken={auction.want_token?.symbol || '—'}
                      />
                    </td>
                    
                    <td>
                      {(() => {
                        const isActive = auction.current_round?.is_active || false
                        const isKickable = kickableData[auction.address]?.isKickable || false
                        const kickableCount = kickableData[auction.address]?.totalKickableCount || 0
                        
                        // Determine all applicable statuses
                        const statuses: AuctionStatus[] = []
                        if (isKickable) statuses.push('kickable')
                        if (isActive) statuses.push('active')
                        if (statuses.length === 0) statuses.push('inactive')
                        
                        return (
                          <div className="flex flex-col space-y-1">
                            {statuses.map((status, index) => {
                              const config = statusConfig[status]
                              return (
                                <div key={status} className="flex items-center space-x-2">
                                  <div className={`h-2 w-2 rounded-full ${config.dotColor} ${config.animated ? 'animate-pulse' : ''}`}></div>
                                  <span className={`text-sm font-medium ${config.textColor}`}>
                                    {config.label}
                                    {status === 'kickable' && kickableCount > 0 && (
                                      <span className="text-xs ml-1">({kickableCount})</span>
                                    )}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        )
                      })()}
                    </td>
                    
                    <td>
                      <div className="flex items-center space-x-1 text-sm">
                        <TrendingDown className="h-3 w-3 text-gray-400" />
                        <span className="font-medium">
                          {auction.decay_rate !== undefined && auction.decay_rate !== null ? 
                            `${(auction.decay_rate * 100).toFixed(2)}%` : 
                            'N/A'
                          }
                        </span>
                      </div>
                    </td>
                    
                    <td className="text-center">
                      <div className="flex items-center justify-center text-sm">
                        <span className="font-medium">
                          {auction.update_interval || 0}s
                        </span>
                      </div>
                    </td>
                    
                    <td>
                      {auction?.last_kicked ? (
                        <span 
                          className="text-sm text-gray-400"
                          title={new Date(auction.last_kicked).toLocaleString()}
                        >
                          {formatTimeAgo(new Date(auction.last_kicked!).getTime() / 1000)}
                        </span>
                      ) : (
                        <span className="text-gray-500 text-sm">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {filteredAndSorted.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <p>No auctions match the current filters</p>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}

export default AuctionsTable
