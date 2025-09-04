import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpDown, ArrowUp, ArrowDown, Search, Trophy, TrendingUp } from 'lucide-react'
import { TakerSummary } from '../types/taker'
import { formatTimeAgo, formatUSD, formatNumber } from '../lib/utils'
import { apiClient } from '../lib/api'
import TakerLink from './TakerLink'

type SortField = 'total_takes' | 'total_volume_usd' | 'last_take_at'
type SortDirection = 'asc' | 'desc'

interface TakersTableProps {
  chainFilter?: number
  limit?: number
}

const TakersTable: React.FC<TakersTableProps> = ({ chainFilter, limit = 50 }) => {
  const [sortField, setSortField] = useState<SortField>('total_takes')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  // Map frontend sort field to API expected values
  const getApiSortBy = (field: SortField): string => {
    switch (field) {
      case 'total_takes': return 'takes'
      case 'total_volume_usd': return 'volume'
      case 'last_take_at': return 'recent'
      default: return 'volume'
    }
  }

  const { data: takersData, isLoading, error } = useQuery({
    queryKey: ['takers', sortField, page, limit, chainFilter],
    queryFn: () => apiClient.getTakers({
      sort_by: getApiSortBy(sortField),
      page,
      limit,
      chain_id: chainFilter
    }),
    refetchInterval: 30000,
  })

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
    setPage(1)
  }

  const handleRankSort = () => {
    // Toggle between total_takes and total_volume_usd for ranking
    if (sortField === 'total_takes') {
      handleSort('total_volume_usd')
    } else {
      handleSort('total_takes')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="h-4 w-4 text-gray-500" />
    return sortDirection === 'asc' 
      ? <ArrowUp className="h-4 w-4 text-primary-400" />
      : <ArrowDown className="h-4 w-4 text-primary-400" />
  }

  // Filter takers based on search
  const filteredTakers = useMemo(() => {
    if (!takersData?.takers || !search.trim()) return takersData?.takers || []
    
    const searchLower = search.toLowerCase()
    return takersData.takers.filter(taker =>
      taker.taker.toLowerCase().includes(searchLower)
    )
  }, [takersData?.takers, search])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">Loading takers...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-red-400">Error loading takers: {error.message}</div>
      </div>
    )
  }

  if (!filteredTakers.length) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-400">No takers found</div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search taker addresses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-800">
        <div className="overflow-x-auto">
          <table className="table">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-left px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={handleRankSort}>
                  <div className="flex items-center space-x-2">
                    <Trophy className="h-4 w-4 text-yellow-400" />
                    <div className="flex flex-col">
                      <span className="font-medium">Rank</span>
                      <span className="text-xs text-gray-400">
                        {sortField === 'total_takes' ? '(count)' : '(USD)'}
                      </span>
                    </div>
                  </div>
                </th>
                <th className="text-left px-4 py-3">
                  <span className="font-medium">Taker</span>
                </th>
                <th className="text-left px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('total_takes')}>
                  <div className="flex items-center space-x-1">
                    <span className="font-medium">Total Takes</span>
                    {getSortIcon('total_takes')}
                  </div>
                </th>
                <th className="text-left px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('total_volume_usd')}>
                  <div className="flex items-center space-x-1">
                    <span className="font-medium">Total Volume</span>
                    {getSortIcon('total_volume_usd')}
                  </div>
                </th>
                <th className="text-left px-4 py-3">
                  <span className="font-medium">Unique Auctions</span>
                </th>
                <th className="text-left px-4 py-3">
                  <span className="font-medium">Avg Take Value</span>
                </th>
                <th className="text-left px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleSort('last_take_at')}>
                  <div className="flex items-center space-x-1">
                    <span className="font-medium">Last Activity</span>
                    {getSortIcon('last_take_at')}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="bg-gray-900">
              {filteredTakers.map((taker, index) => (
                <tr key={taker.taker} className="group hover:bg-gray-800/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-bold text-white">
                        #{sortField === 'total_volume_usd' ? taker.rank_by_volume : taker.rank_by_takes}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <TakerLink 
                      takerAddress={taker.taker} 
                      chainId={taker.active_chains?.[0] || 1} 
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-1">
                      <TrendingUp className="h-3 w-3 text-green-400" />
                      <span className="font-medium text-green-400">
                        {formatNumber(taker.total_takes)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium">
                      {taker.total_volume_usd !== null 
                        ? formatUSD(taker.total_volume_usd)
                        : <span className="text-gray-500">—</span>
                      }
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-300">
                      {formatNumber(taker.unique_auctions)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-300">
                      {taker.avg_take_size_usd !== null 
                        ? formatUSD(taker.avg_take_size_usd)
                        : <span className="text-gray-500">—</span>
                      }
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-400">
                      {taker.last_take ? formatTimeAgo(taker.last_take) : '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {takersData && takersData.has_next && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-400">
            Page {takersData.page} 
            ({takersData.total} total takers)
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={!takersData.has_next}
              className="px-3 py-1 bg-gray-800 border border-gray-700 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-700"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default TakersTable