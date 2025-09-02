import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../lib/api'

interface ChainIconProps {
  chainId: number
  size?: 'xs' | 'sm' | 'md' | 'lg'
  showName?: boolean
  className?: string
}

const ChainIcon: React.FC<ChainIconProps> = ({ 
  chainId, 
  size = 'md', 
  showName = false,
  className = '' 
}) => {
  const [imageError, setImageError] = useState(false)

  // Use React Query to cache chain data efficiently
  const { data: chainInfo } = useQuery({
    queryKey: ['chain', chainId],
    queryFn: () => apiClient.getChain(chainId),
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
    cacheTime: 24 * 60 * 60 * 1000, // 24 hours
    retry: false, // Don't retry failed requests
    refetchOnWindowFocus: false, // Don't refetch when window gains focus
    refetchOnReconnect: false, // Don't refetch on network reconnect
    refetchOnMount: false, // Don't refetch on mount if data exists
    // Transform the data to our expected format
    select: (data) => data ? {
      name: data.name,
      shortName: data.shortName,
      icon: data.icon,
      nativeSymbol: data.nativeSymbol
    } : {
      name: `Chain ${chainId}`,
      shortName: `Chain ${chainId}`,
      icon: null,
      nativeSymbol: 'ETH'
    }
  })

  const sizeClasses = {
    xs: 'h-4 w-4',
    sm: 'h-5 w-5',
    md: 'h-6 w-6', 
    lg: 'h-8 w-8'
  }

  const textSizes = {
    xs: 'text-xs',
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base'
  }

  if (!chainInfo) {
    return (
      <div className={`inline-flex items-center space-x-1 ${className}`}>
        <div className={`${sizeClasses[size]} bg-gray-700 rounded-full animate-pulse`} />
        {showName && <span className={`${textSizes[size]} text-gray-500`}>Unknown</span>}
      </div>
    )
  }

  const handleImageError = () => {
    setImageError(true)
  }

  const containerSpacing = showName ? 'space-x-2' : 'space-x-0'
  return (
    <div className={`inline-flex items-center ${containerSpacing} tooltip ${className}`}>
      {chainInfo.icon && !imageError ? (
        <img 
          src={chainInfo.icon}
          alt={chainInfo.name}
          className={`${sizeClasses[size]} rounded-full bg-gray-800 shrink-0`}
          onError={handleImageError}
          loading="lazy"
        />
      ) : (
        // Fallback: show first letter of chain name in a colored circle
        <div className={`${sizeClasses[size]} bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center shrink-0`}>
          <span className="text-xs font-bold text-white">
            {chainInfo.shortName.charAt(0).toUpperCase()}
          </span>
        </div>
      )}
      
      {showName && (
        <span className={`${textSizes[size]} text-gray-300 font-medium`}>
          {chainInfo.shortName}
        </span>
      )}
      
      <span className="tooltip-text">{chainInfo.name}</span>
    </div>
  )
}

export default ChainIcon
