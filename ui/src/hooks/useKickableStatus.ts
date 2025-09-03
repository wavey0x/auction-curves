/**
 * Hook for efficiently checking kickable status across multiple auctions and tokens
 * Only fetches for real networks, caches aggressively, and minimizes RPC calls
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { type Address } from 'viem'
import { getTokenSpecificAuctionData, type AuctionCall, type TokenSpecificResult } from '../lib/multicall'
import type { AuctionListItem, Token } from '../types/auction'

// Result type for kickable status
export interface KickableResult {
  [auctionAddress: string]: {
    [tokenAddress: string]: {
      kickableAmount: bigint
      isKickable: boolean
    }
  }
}

// Consolidated result with overall kickable status per auction
export interface AuctionKickableStatus {
  [auctionAddress: string]: {
    isKickable: boolean
    kickableTokens: Array<{
      address: string
      symbol: string
      kickableAmount: bigint
    }>
    totalKickableCount: number
  }
}

/**
 * Hook for checking kickable status across visible auctions
 * Only triggers on auction list changes, not UI filtering/sorting
 */
export function useKickableStatus(
  auctions: AuctionListItem[],
  refetchInterval: number = 300000 // 5 minutes - longer cache for kickable
): UseQueryResult<AuctionKickableStatus, Error> {
  
  return useQuery({
    queryKey: ['kickable-status', auctions.map(a => `${a.chain_id}-${a.address}`).sort()],
    queryFn: async () => {
      if (auctions.length === 0) {
        return {}
      }


      // Skip live data for local Anvil network and filter out null auctions
      const realNetworkAuctions = auctions.filter(auction => 
        auction && 
        auction.chain_id !== 31337
      )
      if (realNetworkAuctions.length === 0) {
        return {}
      }

      // Group auctions by chain for efficient multicall batching
      const auctionsByChain: Record<number, AuctionCall[]> = {}
      
      for (const auction of realNetworkAuctions) {
        // Additional safety check for auction and its properties
        if (!auction || !auction.chain_id || !auction.address || !auction.from_tokens) {
          console.warn('Skipping invalid auction object:', auction)
          continue
        }
        
        if (!auctionsByChain[auction.chain_id]) {
          auctionsByChain[auction.chain_id] = []
        }
        
        // Check kickable for each from_token in the auction
        for (const token of auction.from_tokens) {
          if (!token || !token.address) {
            console.warn('Skipping invalid token in auction:', auction.address, token)
            continue
          }
          auctionsByChain[auction.chain_id].push({
            auctionAddress: auction.address as Address,
            fromToken: token.address as Address,
            call: 'kickable'
          })
        }
      }


      // Execute multicalls for each chain in parallel
      const chainResults = await Promise.all(
        Object.entries(auctionsByChain).map(async ([chainId, calls]) => {
          try {
            const results = await getTokenSpecificAuctionData(parseInt(chainId), calls)
            return { chainId: parseInt(chainId), results }
          } catch (error) {
            console.error(`Failed to fetch kickable data for chain ${chainId}:`, error)
            return { chainId: parseInt(chainId), results: {} }
          }
        })
      )

      // Process results into consolidated status
      const consolidatedStatus: AuctionKickableStatus = {}

      // Create lookup map of token addresses to symbols
      const tokenLookup: Record<string, Token> = {}
      for (const auction of realNetworkAuctions) {
        if (!auction || !auction.from_tokens) continue
        for (const token of auction.from_tokens) {
          if (!token || !token.address) continue
          tokenLookup[token.address.toLowerCase()] = token
        }
      }

      for (const { chainId, results } of chainResults) {
        for (const [auctionAddress, tokenResults] of Object.entries(results)) {
          if (!consolidatedStatus[auctionAddress]) {
            consolidatedStatus[auctionAddress] = {
              isKickable: false,
              kickableTokens: [],
              totalKickableCount: 0
            }
          }

          // Process each token's results for this auction
          for (const [tokenAddress, tokenData] of Object.entries(tokenResults)) {
            
            // Check if this specific token has kickable amount > 0
            if (tokenData.kickable !== undefined && tokenData.kickable > 0n) {
              const tokenInfo = tokenLookup[tokenAddress.toLowerCase()]
              if (tokenInfo) {
                consolidatedStatus[auctionAddress].kickableTokens.push({
                  address: tokenAddress,
                  symbol: tokenInfo.symbol,
                  kickableAmount: tokenData.kickable
                })
                
                // Mark the entire auction as kickable if any token is kickable
                consolidatedStatus[auctionAddress].isKickable = true
                consolidatedStatus[auctionAddress].totalKickableCount++
              }
            }
          }
        }
      }

      const kickableCount = Object.values(consolidatedStatus).filter(status => status.isKickable).length

      return consolidatedStatus
    },
    refetchInterval,
    staleTime: 240000, // Consider data stale after 4 minutes  
    gcTime: 600000, // Keep in cache for 10 minutes after unmount
    enabled: auctions.length > 0
  })
}

/**
 * Hook for getting kickable status of a single auction
 */
export function useAuctionKickableStatus(
  auction: AuctionListItem | null,
  refetchInterval: number = 300000
): UseQueryResult<AuctionKickableStatus[string], Error> {
  
  const { data: allKickableStatus, ...rest } = useKickableStatus(auction ? [auction] : [], refetchInterval)
  
  return {
    ...rest,
    data: (auction && allKickableStatus?.[auction.address]) || {
      isKickable: false,
      kickableTokens: [],
      totalKickableCount: 0
    }
  }
}