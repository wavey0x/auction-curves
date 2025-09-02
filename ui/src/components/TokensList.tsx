import React, { useState, useMemo } from 'react'
import { Search, ChevronDown, ChevronUp } from 'lucide-react'
import { Token } from '../types/auction'
import { cn } from '../lib/utils'
import TokenWithAddress from './TokenWithAddress'

type DisplayMode = 'inline' | 'grid'

interface TokensListProps {
  tokens: Token[]
  maxDisplay?: number
  className?: string
  tokenClassName?: string
  separator?: string
  // Enhanced props
  displayMode?: DisplayMode
  expandable?: boolean
  showSearch?: boolean
  gridColumns?: number
  maxHeight?: string
  // Address feature props
  showAddressFeatures?: boolean
  chainId?: number
}

const TokensList: React.FC<TokensListProps> = ({
  tokens,
  maxDisplay = 2,
  className = '',
  tokenClassName = 'text-primary-400 font-medium',
  separator = ', ',
  // Enhanced props with defaults
  displayMode = 'inline',
  expandable = false,
  showSearch = false,
  gridColumns = 3,
  maxHeight = 'max-h-64',
  // Address feature props
  showAddressFeatures = false,
  chainId
}) => {
  const [showTooltipState, setShowTooltipState] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20

  // Filter tokens based on search term
  const filteredTokens = useMemo(() => {
    if (!showSearch || !searchTerm.trim()) return tokens
    return tokens.filter(token => 
      token.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      token.name?.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [tokens, searchTerm, showSearch])

  // Pagination logic
  const totalPages = Math.ceil(filteredTokens.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const paginatedTokens = filteredTokens.slice(startIndex, endIndex)

  if (!tokens || tokens.length === 0) {
    return <span className="text-gray-500">No tokens</span>
  }

  // Grid display mode
  if (displayMode === 'grid') {
    const tokensToShow = isExpanded ? (tokens.length > 50 ? paginatedTokens : filteredTokens) : tokens.slice(0, maxDisplay)
    const shouldShowExpand = expandable && tokens.length > maxDisplay
    const shouldShowPagination = isExpanded && tokens.length > 50
    
    return (
      <div className={cn('space-y-3', className)}>
        {/* Search bar for large lists */}
        {showSearch && isExpanded && (
          <div className="relative max-w-xs mx-auto">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 text-gray-500" />
            <input
              type="text"
              placeholder="Search tokens..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1) // Reset page when searching
              }}
              className="w-full pl-7 pr-3 py-1 text-xs bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-primary-500"
            />
          </div>
        )}
        
        {/* Token grid */}
        <div className={cn(
          'grid gap-1 justify-items-start',
          `grid-cols-${gridColumns}`,
          isExpanded && maxHeight,
          isExpanded && 'overflow-y-auto'
        )}>
          {tokensToShow.map((token) => (
            showAddressFeatures && chainId ? (
              <TokenWithAddress
                key={token.address}
                token={token}
                chainId={chainId}
                className={tokenClassName}
              />
            ) : (
              <span 
                key={token.address} 
                className={cn(
                  'px-2 py-1 bg-gray-800 rounded-full text-xs border border-gray-700 hover:border-primary-500 transition-colors',
                  tokenClassName
                )}
                title={token.name || token.symbol}
              >
                {token.symbol}
              </span>
            )
          ))}
        </div>
        
        {/* Pagination for very large lists */}
        {shouldShowPagination && totalPages > 1 && (
          <div className="flex items-center justify-center space-x-2 pt-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className={cn(
                'w-6 h-6 flex items-center justify-center rounded text-xs font-medium transition-all',
                currentPage === 1 
                  ? 'text-gray-600 cursor-not-allowed' 
                  : 'text-gray-300 hover:text-white hover:bg-gray-700'
              )}
            >
              ‹
            </button>
            
            <span className="text-xs text-gray-400 px-2">
              {currentPage} / {totalPages}
            </span>
            
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className={cn(
                'w-6 h-6 flex items-center justify-center rounded text-xs font-medium transition-all',
                currentPage === totalPages 
                  ? 'text-gray-600 cursor-not-allowed' 
                  : 'text-gray-300 hover:text-white hover:bg-gray-700'
              )}
            >
              ›
            </button>
          </div>
        )}
        
        {/* Expand/Collapse button */}
        {shouldShowExpand && (
          <div className="flex justify-center pt-1">
            <button
              onClick={() => {
                setIsExpanded(!isExpanded)
                if (!isExpanded) {
                  setSearchTerm('')
                  setCurrentPage(1)
                }
              }}
              className="flex items-center space-x-1 text-xs text-gray-400 hover:text-primary-400 transition-colors"
            >
              {isExpanded ? (
                <>
                  <span>Show less</span>
                  <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  <span>+{tokens.length - maxDisplay} more</span>
                  <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    )
  }
  
  // Inline display mode (existing behavior)
  if (tokens.length <= maxDisplay) {
    return (
      <div className={`flex flex-wrap gap-1 ${className}`}>
        {tokens.map((token, index) => (
          <span key={token.address} className={tokenClassName}>
            {token.symbol}
            {index < tokens.length - 1 ? separator.trim() : ''}
          </span>
        ))}
      </div>
    )
  }

  // Show condensed view with tooltip
  const visibleTokens = tokens.slice(0, maxDisplay)
  const remainingCount = tokens.length - maxDisplay

  return (
    <div className={`flex flex-wrap gap-1 ${className}`}>
      {/* Show first few tokens */}
      {visibleTokens.map((token, index) => (
        <span key={token.address} className={tokenClassName}>
          {token.symbol}
          {index < visibleTokens.length - 1 ? separator.trim() : ''}
        </span>
      ))}
      
      {/* Show "+X more" with tooltip */}
      <div 
        className="relative inline-block"
        onMouseEnter={() => setShowTooltipState(true)}
        onMouseLeave={() => setShowTooltipState(false)}
      >
        <span className={`cursor-help border-b border-dotted border-gray-400 ${tokenClassName}`}>
          +{remainingCount}
        </span>
        
        {/* Tooltip */}
        {showTooltipState && (
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
            <div className="bg-gray-800 text-white text-xs rounded-lg py-2 px-3 shadow-lg border border-gray-700 min-w-max">
              <div className="text-gray-300 mb-1 font-medium">All tokens:</div>
              <div className="flex flex-wrap gap-1">
                {tokens.map((token, index) => (
                  <span key={token.address} className="text-primary-400">
                    {token.symbol}
                    {index < tokens.length - 1 ? ',' : ''}
                  </span>
                ))}
              </div>
              {/* Tooltip arrow */}
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default TokensList