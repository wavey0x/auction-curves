import React, { useState } from 'react'
import { Token } from '../types/auction'

interface TokensListProps {
  tokens: Token[]
  maxDisplay?: number
  className?: string
  tokenClassName?: string
  separator?: string
}

const TokensList: React.FC<TokensListProps> = ({
  tokens,
  maxDisplay = 2,
  className = '',
  tokenClassName = 'text-primary-400 font-medium',
  separator = ', '
}) => {
  const [showTooltip, setShowTooltip] = useState(false)

  if (!tokens || tokens.length === 0) {
    return <span className="text-gray-500">No tokens</span>
  }

  // If we have fewer tokens than the max, show them all normally
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
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span className={`cursor-help border-b border-dotted border-gray-400 ${tokenClassName}`}>
          +{remainingCount}
        </span>
        
        {/* Tooltip */}
        {showTooltip && (
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