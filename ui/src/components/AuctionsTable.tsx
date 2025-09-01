import React, { useState, useMemo, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { 
  Activity, 
  ArrowUpDown, 
  ArrowUp, 
  ArrowDown,
  Search,
  Filter,
  Clock,
  TrendingDown,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Home
} from 'lucide-react'
import type { AuctionListItem } from '../types/auction'
import { formatAddress, formatTokenAmount, formatTimeAgo } from '../lib/utils'
import { apiClient } from '../lib/api'
import StackedProgressMeter from './StackedProgressMeter'
import ChainIcon from './ChainIcon'
import TokensList from './TokensList'

interface AuctionsTableProps {
  auctions: AuctionListItem[]
}

type SortField = 'address' | 'status' | 'decay_rate' | 'update_interval' | 'last_kicked'
type SortDirection = 'asc' | 'desc'

const AuctionsTable: React.FC<AuctionsTableProps> = ({ auctions = [] }) => {
  const [search, setSearch] = useState('')
  const [tokenFilter, setTokenFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [chainFilter, setChainFilter] = useState('')
  const [chainDropdownOpen, setChainDropdownOpen] = useState(false)
  const [sortField, setSortField] = useState<SortField>('address')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setChainDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Extract unique values for filters

  const uniqueTokens = useMemo(() => {
    const tokens = new Set<string>()
    auctions?.forEach(ah => {
      ah.from_tokens?.forEach(token => {
        if (token?.symbol) {
          tokens.add(token.symbol)
        }
        if (token?.address) {
          tokens.add(token.address.toLowerCase())
        }
      })
      if (ah.want_token?.symbol && ah.want_token?.address) {
        tokens.add(ah.want_token.symbol)
        tokens.add(ah.want_token.address.toLowerCase())
      }
    })
    return Array.from(tokens).sort()
  }, [auctions])

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
        const tokenLower = tokenFilter.toLowerCase()
        const hasFromToken = ah.from_tokens?.some(token =>
          token.symbol?.toLowerCase().includes(tokenLower) ||
          token.address?.toLowerCase().includes(tokenLower)
        ) || false
        const hasWantToken = 
          ah.want_token?.symbol?.toLowerCase().includes(tokenLower) ||
          ah.want_token?.address?.toLowerCase().includes(tokenLower)
        
        if (!hasFromToken && !hasWantToken) {
          return false
        }
      }


      // Status filter
      if (statusFilter) {
        const isActive = ah.current_round?.is_active || false
        if ((statusFilter === 'active' && !isActive) || (statusFilter === 'inactive' && isActive)) {
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
          aVal = a.current_round?.is_active ? 1 : 0
          bVal = b.current_round?.is_active ? 1 : 0
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
  }, [auctions, search, tokenFilter, statusFilter, chainFilter, sortField, sortDirection])

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
    <div className="space-y-2">
      {/* Compact filters with results badge on same line */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex flex-wrap gap-2 items-center flex-1">
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
          
          <select
            className="w-full sm:w-32 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            value={tokenFilter}
            onChange={(e) => setTokenFilter(e.target.value)}
          >
            <option value="">All Tokens</option>
            {uniqueTokens.map(token => (
              <option key={token} value={token}>{token}</option>
            ))}
          </select>
          
          <select
            className="w-full sm:w-28 px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          
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
          
          <button
            onClick={() => {
              setSearch('')
              setTokenFilter('')
              setStatusFilter('')
              setChainFilter('')
            }}
            className="w-full sm:w-20 px-2 py-1 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded text-xs transition-colors flex items-center justify-center space-x-1"
          >
            <Filter className="h-3 w-3" />
            <span>Clear</span>
          </button>
        </div>
        
        <span className="badge badge-neutral text-xs whitespace-nowrap">Results: {filteredAndSorted.length}</span>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-800">

      {/* Table */}
      <div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead className="bg-gray-800/50">
              <tr>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('address')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Address</span>
                    <SortIcon field="address" />
                  </div>
                </th>
                <th className="text-center w-16">Chain</th>
                <th className="text-center">Trading</th>
                <th 
                  className="cursor-pointer select-none hover:bg-gray-700/50 text-center"
                  onClick={() => handleSort('status')}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span>Status</span>
                    <SortIcon field="status" />
                  </div>
                </th>
                <th className="text-center">Current Round</th>
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
                    <td>
                      <Link
                        to={`/auction/${auction?.chain_id}/${auction?.address}`}
                        className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors"
                      >
                        {formatAddress(auction?.address || '')}
                      </Link>
                    </td>
                    
                    <td className="w-16 text-center">
                      <div className="flex justify-center">
                        <ChainIcon 
                          chainId={auction?.chain_id || 31337} 
                          size="sm"
                          showName={false}
                        />
                      </div>
                    </td>
                    
                    <td>
                      <div className="flex items-center space-x-2 text-sm">
                        <TokensList 
                          tokens={auction.from_tokens || []}
                          maxDisplay={2}
                          tokenClassName="text-primary-400 font-medium"
                        />
                        <span className="text-gray-500">→</span>
                        <span className="text-yellow-400 font-medium">
                          {auction.want_token?.symbol}
                        </span>
                      </div>
                    </td>
                    
                    
                    <td>
                      <div className="flex items-center space-x-2">
                        <div className={`h-2 w-2 rounded-full ${
                          isActive ? 'bg-success-500 animate-pulse' : 'bg-gray-600'
                        }`}></div>
                        <span className={`text-sm font-medium ${
                          isActive ? 'text-success-400' : 'text-gray-500'
                        }`}>
                          {isActive ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </td>
                    
                    <td>
                      {currentRound ? (
                        <Link
                          to={`/round/${auction?.chain_id}/${auction?.address}/${currentRound?.round_id}`}
                          className="inline-flex items-center space-x-1 px-2 py-0.5 hover:bg-gray-800/30 rounded transition-all duration-200 group"
                        >
                          <span className="font-mono text-sm font-semibold text-gray-300 group-hover:text-primary-300">
                            R{currentRound.round_id}
                          </span>
                        </Link>
                      ) : (
                        <span className="text-gray-500 text-sm">—</span>
                      )}
                    </td>
                    
                    <td>
                      <div className="flex items-center space-x-1 text-sm">
                        <TrendingDown className="h-3 w-3 text-gray-400" />
                        <span className="font-medium">
                          {((auction.decay_rate || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    
                    <td>
                      <div className="flex items-center space-x-1 text-sm">
                        <Clock className="h-3 w-3 text-gray-400" />
                        <span className="font-medium">
                          {((auction.update_interval || 0) / 60).toFixed(1)}m
                        </span>
                      </div>
                    </td>
                    
                    <td>
                      {auction?.last_kicked ? (
                        <span className="text-sm text-gray-400">
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
            <p>No Auction Houses match the current filters</p>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}

export default AuctionsTable