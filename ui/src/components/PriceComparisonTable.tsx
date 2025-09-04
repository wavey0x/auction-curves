import React, { useState } from 'react'
import { ArrowUpDown, TrendingUp, TrendingDown, Clock, Hash } from 'lucide-react'
import { formatUSD, formatNumber, cn } from '../lib/utils'

interface PriceQuote {
  source: string
  token_address: string
  token_symbol?: string
  price_usd: number
  block_number: number
  timestamp: number
  block_distance: number
  time_distance: number
}

interface PnLScenario {
  from_source: string
  to_source: string
  from_price: number
  to_price: number
  pnl: number
  pnl_percent: number
  effective_rate: number
}

interface PriceComparisonTableProps {
  fromTokenQuotes: PriceQuote[]
  toTokenQuotes: PriceQuote[]
  amountTaken: number
  amountPaid: number
  fromTokenSymbol: string
  toTokenSymbol: string
  className?: string
}

type SortField = 'source' | 'pnl' | 'pnl_percent' | 'block_distance' | 'time_distance'
type SortDirection = 'asc' | 'desc'

const PriceComparisonTable: React.FC<PriceComparisonTableProps> = ({
  fromTokenQuotes,
  toTokenQuotes,
  amountTaken,
  amountPaid,
  fromTokenSymbol,
  toTokenSymbol,
  className
}) => {
  const [sortField, setSortField] = useState<SortField>('pnl')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  // Generate PnL scenarios for all price combinations
  const pnlScenarios: PnLScenario[] = []
  
  for (const fromQuote of fromTokenQuotes) {
    for (const toQuote of toTokenQuotes) {
      const fromValue = amountTaken * fromQuote.price_usd
      const toValue = amountPaid * toQuote.price_usd
      const pnl = fromValue - toValue
      const pnlPercent = toValue > 0 ? (pnl / toValue) * 100 : 0
      const effectiveRate = fromQuote.price_usd / toQuote.price_usd
      
      pnlScenarios.push({
        from_source: fromQuote.source,
        to_source: toQuote.source,
        from_price: fromQuote.price_usd,
        to_price: toQuote.price_usd,
        pnl,
        pnl_percent: pnlPercent,
        effective_rate: effectiveRate
      })
    }
  }

  // Sort scenarios
  const sortedScenarios = [...pnlScenarios].sort((a, b) => {
    let aVal, bVal
    
    switch (sortField) {
      case 'source':
        aVal = `${a.from_source}-${a.to_source}`
        bVal = `${b.from_source}-${b.to_source}`
        break
      case 'pnl':
        aVal = a.pnl
        bVal = b.pnl
        break
      case 'pnl_percent':
        aVal = a.pnl_percent
        bVal = b.pnl_percent
        break
      default:
        aVal = a.pnl
        bVal = b.pnl
    }
    
    if (typeof aVal === 'string') {
      return sortDirection === 'asc' ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal)
    }
    
    return sortDirection === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
  })

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const SortableHeader: React.FC<{ field: SortField; children: React.ReactNode }> = ({ field, children }) => (
    <th
      className="text-left px-3 py-2 cursor-pointer hover:bg-gray-700/50 transition-colors select-none"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center space-x-1">
        <span>{children}</span>
        <ArrowUpDown className="h-3 w-3 text-gray-500" />
        {sortField === field && (
          <span className="text-primary-400 ml-1">
            {sortDirection === 'desc' ? '↓' : '↑'}
          </span>
        )}
      </div>
    </th>
  )

  // Find best and worst scenarios
  const bestScenario = sortedScenarios.reduce((best, current) => 
    current.pnl > best.pnl ? current : best, sortedScenarios[0])
  const worstScenario = sortedScenarios.reduce((worst, current) => 
    current.pnl < worst.pnl ? current : worst, sortedScenarios[0])

  if (pnlScenarios.length === 0) {
    return (
      <div className={cn("card", className)}>
        <h3 className="text-lg font-semibold mb-4">Price Comparison</h3>
        <div className="text-center py-8 text-gray-500">
          <Clock className="h-8 w-8 mx-auto mb-2" />
          <p>No price quotes available around the time of this take</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("card", className)}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">Price Comparison & PnL Analysis</h3>
        <div className="flex items-center space-x-4 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-green-400"></div>
            <span className="text-gray-400">Best: {formatUSD(bestScenario.pnl)}</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-red-400"></div>
            <span className="text-gray-400">Worst: {formatUSD(worstScenario.pnl)}</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead className="bg-gray-800/50">
            <tr>
              <SortableHeader field="source">Source Pair</SortableHeader>
              <th className="text-left px-3 py-2">{fromTokenSymbol} Price</th>
              <th className="text-left px-3 py-2">{toTokenSymbol} Price</th>
              <th className="text-left px-3 py-2">Effective Rate</th>
              <SortableHeader field="pnl">PnL (USD)</SortableHeader>
              <SortableHeader field="pnl_percent">PnL %</SortableHeader>
            </tr>
          </thead>
          <tbody>
            {sortedScenarios.map((scenario, index) => {
              const isBest = scenario.pnl === bestScenario.pnl
              const isWorst = scenario.pnl === worstScenario.pnl
              const pnlPositive = scenario.pnl >= 0
              
              return (
                <tr 
                  key={`${scenario.from_source}-${scenario.to_source}-${index}`}
                  className={cn(
                    "hover:bg-gray-800/30 transition-colors",
                    isBest && "bg-green-900/20 border-l-2 border-green-400",
                    isWorst && "bg-red-900/20 border-l-2 border-red-400"
                  )}
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center space-x-2">
                      <div className="flex items-center space-x-1">
                        <span className="px-2 py-1 bg-gray-700 rounded text-xs font-mono">
                          {scenario.from_source.toUpperCase()}
                        </span>
                        <span className="text-gray-500">×</span>
                        <span className="px-2 py-1 bg-gray-700 rounded text-xs font-mono">
                          {scenario.to_source.toUpperCase()}
                        </span>
                      </div>
                      {isBest && <TrendingUp className="h-3 w-3 text-green-400" />}
                      {isWorst && <TrendingDown className="h-3 w-3 text-red-400" />}
                    </div>
                  </td>
                  
                  <td className="px-3 py-2 font-mono text-sm">
                    {formatUSD(scenario.from_price)}
                  </td>
                  
                  <td className="px-3 py-2 font-mono text-sm">
                    {formatUSD(scenario.to_price)}
                  </td>
                  
                  <td className="px-3 py-2 font-mono text-sm text-gray-300">
                    {formatNumber(scenario.effective_rate, 4)}
                  </td>
                  
                  <td className="px-3 py-2">
                    <span className={cn(
                      "font-mono font-medium",
                      pnlPositive ? "text-green-400" : "text-red-400"
                    )}>
                      {pnlPositive ? '+' : ''}{formatUSD(scenario.pnl)}
                    </span>
                  </td>
                  
                  <td className="px-3 py-2">
                    <span className={cn(
                      "font-mono font-medium",
                      pnlPositive ? "text-green-400" : "text-red-400"
                    )}>
                      {pnlPositive ? '+' : ''}{scenario.pnl_percent.toFixed(2)}%
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-xs text-gray-500 bg-gray-800/30 p-3 rounded">
        <div className="flex items-center space-x-1 mb-1">
          <Hash className="h-3 w-3" />
          <span className="font-semibold">Price Sources Explanation:</span>
        </div>
        <ul className="space-y-1 ml-4">
          <li><strong>YPM:</strong> Y Price Magic (historical on-chain prices)</li>
          <li><strong>ENSO:</strong> Enso Finance (DEX aggregation quotes)</li>
          <li><strong>ODOS:</strong> Odos Finance (routing optimization quotes)</li>
          <li><strong>COWSWAP:</strong> CoW Protocol (batch auction prices)</li>
        </ul>
        <p className="mt-2">
          PnL calculated as: (Amount Taken × From Token Price) - (Amount Paid × To Token Price)
        </p>
      </div>
    </div>
  )
}

export default PriceComparisonTable