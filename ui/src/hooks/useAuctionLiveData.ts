/**
 * React hooks for fetching live auction data from blockchain
 * Integrates multicall service with React Query for caching and state management
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { type Address } from 'viem'
import { 
  getAuctionLiveData, 
  getSingleAuctionLiveData,
  type AuctionCall, 
  type AuctionLiveData 
} from '../lib/multicall'
import type { AuctionListItem } from '../types/auction'

// Hook for getting live data for multiple auctions (used in tables)
export function useAuctionsLiveData(
  auctions: AuctionListItem[],
  refetchInterval: number = 30000 // 30 seconds
): UseQueryResult<Record<string, AuctionLiveData>, Error> {
  
  // Create a stable query key to prevent hook violations
  const stableAuctions = auctions || []
  const queryKey = ['auctions-live-data', stableAuctions.map(a => a?.address).filter(Boolean).sort()]
  
  return useQuery({
    queryKey,
    queryFn: async () => {
      if (stableAuctions.length === 0) {
        return {}
      }

      // Skip live data for local Anvil network
      const hasAnvilOnlyAuctions = stableAuctions.every(auction => auction?.chain_id === 31337)
      if (hasAnvilOnlyAuctions) {
        console.log('Skipping live data fetch - local Anvil network detected')
        return {}
      }

      // Group auctions by chain for efficient multicall batching
      const auctionsByChain: Record<number, AuctionCall[]> = {}
      
      for (const auction of stableAuctions) {
        if (!auction || !auction.chain_id || !auction.address) continue
        
        if (!auctionsByChain[auction.chain_id]) {
          auctionsByChain[auction.chain_id] = []
        }
        
        // Add both available and price calls for each auction
        // Use the first from_token if multiple exist
        const fromTokenAddress = auction.from_tokens?.[0]?.address
        if (fromTokenAddress) {
          auctionsByChain[auction.chain_id].push(
            {
              auctionAddress: auction.address as Address,
              fromToken: fromTokenAddress as Address,
              call: 'available'
            },
            {
              auctionAddress: auction.address as Address,
              fromToken: fromTokenAddress as Address,
              call: 'getAmountNeeded'
            }
          )
        }
      }

      // Execute multicalls for each chain in parallel
      const chainResults = await Promise.all(
        Object.entries(auctionsByChain).map(async ([chainId, calls]) => {
          try {
            const results = await getAuctionLiveData(parseInt(chainId), calls)
            return results
          } catch (error) {
            console.error(`Failed to fetch live data for chain ${chainId}:`, error)
            // Return empty results for failed chains
            return {}
          }
        })
      )

      // Merge results from all chains
      const combinedResults: Record<string, AuctionLiveData> = {}
      for (const chainResult of chainResults) {
        Object.assign(combinedResults, chainResult)
      }

      return combinedResults
    },
    refetchInterval,
    staleTime: 25000, // Consider data stale after 25 seconds
    gcTime: 60000, // Keep in cache for 1 minute after unmount
    enabled: stableAuctions.length > 0
  })
}

// Hook for getting live data for a single auction (used in detail pages)
export function useAuctionLiveData(
  auctionAddress: string,
  fromTokenAddress: string,
  chainId: number,
  refetchInterval: number = 30000
): UseQueryResult<AuctionLiveData, Error> {
  
  return useQuery({
    queryKey: ['auction-live-data', auctionAddress, fromTokenAddress, chainId],
    queryFn: async () => {
      // Skip live data for local Anvil network
      if (chainId === 31337) {
        console.log('Skipping live data fetch - local Anvil network')
        return { isLoading: false, error: 'Live data not available for local network' }
      }

      return await getSingleAuctionLiveData(
        chainId,
        auctionAddress as Address,
        fromTokenAddress as Address
      )
    },
    refetchInterval,
    staleTime: 25000,
    gcTime: 60000,
    enabled: !!auctionAddress && !!fromTokenAddress && !!chainId && chainId !== 31337
  })
}

// Hook for getting live data for active auctions only (performance optimization)
export function useActiveAuctionsLiveData(
  allAuctions: AuctionListItem[],
  refetchInterval: number = 30000
): UseQueryResult<Record<string, AuctionLiveData>, Error> {
  
  // Ensure we always have a stable array reference to prevent hook violations
  const stableAllAuctions = allAuctions || []
  
  // Filter to only active auctions to reduce blockchain calls
  const activeAuctions = stableAllAuctions.filter(auction => auction?.current_round?.is_active)
  
  return useAuctionsLiveData(activeAuctions, refetchInterval)
}

// Utility hook for formatting live data values
export function useFormattedAuctionLiveData(
  auctionAddress: string,
  fromTokenAddress: string,
  chainId: number,
  fromTokenDecimals: number = 18,
  refetchInterval: number = 30000
) {
  const { data: liveData, isLoading, error } = useAuctionLiveData(
    auctionAddress,
    fromTokenAddress, 
    chainId,
    refetchInterval
  )

  // Format bigint values to readable numbers
  const formatTokenAmount = (value: bigint | undefined): number | undefined => {
    if (value === undefined) return undefined
    return Number(value) / Math.pow(10, fromTokenDecimals)
  }

  return {
    available: formatTokenAmount(liveData?.available),
    currentPrice: formatTokenAmount(liveData?.amountNeeded), 
    isLoading: isLoading || liveData?.isLoading,
    error: error?.message || liveData?.error,
    isLive: !isLoading && !error && liveData && !liveData.error
  }
}