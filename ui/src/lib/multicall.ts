/**
 * Multicall service for batching blockchain calls
 * Uses viem's built-in multicall3 support for efficient batch reading
 */

import { type Address, type Abi } from 'viem'
import { getRPCClient, rpcService } from './rpcService'

// Minimal ABI for auction contract functions we need
export const AUCTION_ABI = [
  {
    name: 'available',
    type: 'function',
    stateMutability: 'view',
    inputs: [
      { name: '_from', type: 'address' }
    ],
    outputs: [
      { name: '', type: 'uint256' }
    ]
  },
  {
    name: 'getAmountNeeded',
    type: 'function', 
    stateMutability: 'view',
    inputs: [
      { name: '_from', type: 'address' }
    ],
    outputs: [
      { name: '', type: 'uint256' }
    ]
  },
  {
    name: 'kickable',
    type: 'function',
    stateMutability: 'view',
    inputs: [
      { name: '_from', type: 'address' }
    ],
    outputs: [
      { name: '', type: 'uint256' }
    ]
  }
] as const

// Type for a single multicall contract call
export interface MulticallContract {
  address: Address
  abi: Abi
  functionName: string
  args?: readonly unknown[]
}

// Type for auction-specific calls
export interface AuctionCall {
  auctionAddress: Address
  fromToken: Address
  call: 'available' | 'getAmountNeeded' | 'kickable'
}

// Result type for auction live data
export interface AuctionLiveData {
  available?: bigint
  amountNeeded?: bigint
  kickable?: bigint
  isLoading: boolean
  error?: string
}

// Result type for token-specific auction data
export interface TokenSpecificResult {
  [tokenAddress: string]: {
    available?: bigint
    amountNeeded?: bigint
    kickable?: bigint
  }
}

class MulticallService {
  /**
   * Execute multiple contract calls in a single RPC request
   */
  async multicall(
    chainId: number, 
    contracts: MulticallContract[]
  ): Promise<any[]> {
    const client = await getRPCClient(chainId)
    if (!client) {
      if (rpcService.isCustomRPCEnabled()) {
        rpcService.reportCustomRPCError(new Error(`No RPC client available for chain ${chainId}`))
      }
      throw new Error(`No RPC client available for chain ${chainId}`)
    }

    try {
      const results = await client.multicall({
        contracts: contracts.map(contract => ({
          address: contract.address,
          abi: contract.abi,
          functionName: contract.functionName,
          args: contract.args
        }))
      })

      return results.map((result, index) => {
        if (result.status === 'success') {
          return result.result
        } else {
          // Log failures, especially for kickable since it should never revert
          if (contracts[index].functionName === 'kickable') {
            console.warn(`Kickable call failed for ${contracts[index].address}:`, result.error)
          }
          return null
        }
      })
    } catch (error) {
      console.error(`Multicall batch failed for chain ${chainId}:`, error)
      // If custom RPC is enabled, notify to surface a warning in the UI
      if (rpcService.isCustomRPCEnabled()) {
        rpcService.reportCustomRPCError(error)
      }
      throw error
    }
  }

  /**
   * Batch auction calls for multiple auctions
   */
  async getAuctionLiveData(
    chainId: number,
    auctionCalls: AuctionCall[]
  ): Promise<Record<string, AuctionLiveData>> {
    if (auctionCalls.length === 0) {
      return {}
    }

    try {
      // Build contracts array for multicall
      const contracts: MulticallContract[] = []
      const callMap: Array<{ auctionAddress: string, fromToken: string, call: string }> = []

      for (const auctionCall of auctionCalls) {
        if (auctionCall.call === 'available') {
          contracts.push({
            address: auctionCall.auctionAddress,
            abi: AUCTION_ABI,
            functionName: 'available',
            args: [auctionCall.fromToken]
          })
          callMap.push({ 
            auctionAddress: auctionCall.auctionAddress, 
            fromToken: auctionCall.fromToken,
            call: 'available' 
          })
        }

        if (auctionCall.call === 'getAmountNeeded') {
          contracts.push({
            address: auctionCall.auctionAddress,
            abi: AUCTION_ABI,
            functionName: 'getAmountNeeded',
            args: [auctionCall.fromToken]
          })
          callMap.push({ 
            auctionAddress: auctionCall.auctionAddress, 
            fromToken: auctionCall.fromToken,
            call: 'getAmountNeeded' 
          })
        }

        if (auctionCall.call === 'kickable') {
          contracts.push({
            address: auctionCall.auctionAddress,
            abi: AUCTION_ABI,
            functionName: 'kickable',
            args: [auctionCall.fromToken]
          })
          callMap.push({ 
            auctionAddress: auctionCall.auctionAddress, 
            fromToken: auctionCall.fromToken,
            call: 'kickable' 
          })
        }
      }

      // Execute multicall
      const results = await this.multicall(chainId, contracts)

      // Group results by auction address
      const auctionData: Record<string, AuctionLiveData> = {}
      
      for (let i = 0; i < results.length; i++) {
        const { auctionAddress, call } = callMap[i]
        const result = results[i]

        if (!auctionData[auctionAddress]) {
          auctionData[auctionAddress] = {
            isLoading: false
          }
        }

        if (call === 'available') {
          auctionData[auctionAddress].available = result != null ? BigInt(result.toString()) : undefined
        } else if (call === 'getAmountNeeded') {
          auctionData[auctionAddress].amountNeeded = result != null ? BigInt(result.toString()) : undefined
        } else if (call === 'kickable') {
          auctionData[auctionAddress].kickable = result != null ? BigInt(result.toString()) : undefined
        }
      }

      return auctionData

    } catch (error) {
      console.error('Failed to get auction live data:', error)
      
      // Return error state for all auctions
      const errorData: Record<string, AuctionLiveData> = {}
      for (const auctionCall of auctionCalls) {
        errorData[auctionCall.auctionAddress] = {
          isLoading: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        }
      }
      return errorData
    }
  }

  /**
   * Get token-specific auction live data (preserving per-token results)
   */
  async getTokenSpecificAuctionData(
    chainId: number,
    auctionCalls: AuctionCall[]
  ): Promise<Record<string, TokenSpecificResult>> {
    if (auctionCalls.length === 0) {
      return {}
    }

    try {
      // Build contracts array for multicall
      const contracts: MulticallContract[] = []
      const callMap: Array<{ auctionAddress: string, fromToken: string, call: string }> = []

      for (const auctionCall of auctionCalls) {
        if (auctionCall.call === 'available') {
          contracts.push({
            address: auctionCall.auctionAddress,
            abi: AUCTION_ABI,
            functionName: 'available',
            args: [auctionCall.fromToken]
          })
          callMap.push({ 
            auctionAddress: auctionCall.auctionAddress, 
            fromToken: auctionCall.fromToken,
            call: 'available' 
          })
        }

        if (auctionCall.call === 'getAmountNeeded') {
          contracts.push({
            address: auctionCall.auctionAddress,
            abi: AUCTION_ABI,
            functionName: 'getAmountNeeded',
            args: [auctionCall.fromToken]
          })
          callMap.push({ 
            auctionAddress: auctionCall.auctionAddress, 
            fromToken: auctionCall.fromToken,
            call: 'getAmountNeeded' 
          })
        }

        if (auctionCall.call === 'kickable') {
          contracts.push({
            address: auctionCall.auctionAddress,
            abi: AUCTION_ABI,
            functionName: 'kickable',
            args: [auctionCall.fromToken]
          })
          callMap.push({ 
            auctionAddress: auctionCall.auctionAddress, 
            fromToken: auctionCall.fromToken,
            call: 'kickable' 
          })
        }
      }

      // Execute multicall
      const results = await this.multicall(chainId, contracts)

      // Group results by auction address AND token address
      const auctionTokenData: Record<string, TokenSpecificResult> = {}
      
      for (let i = 0; i < results.length; i++) {
        const { auctionAddress, fromToken, call } = callMap[i]
        const result = results[i]

        if (!auctionTokenData[auctionAddress]) {
          auctionTokenData[auctionAddress] = {}
        }

        if (!auctionTokenData[auctionAddress][fromToken]) {
          auctionTokenData[auctionAddress][fromToken] = {}
        }

        if (call === 'available') {
          auctionTokenData[auctionAddress][fromToken].available = result != null ? BigInt(result.toString()) : undefined
        } else if (call === 'getAmountNeeded') {
          auctionTokenData[auctionAddress][fromToken].amountNeeded = result != null ? BigInt(result.toString()) : undefined
        } else if (call === 'kickable') {
          auctionTokenData[auctionAddress][fromToken].kickable = result != null ? BigInt(result.toString()) : undefined
        }
      }

      return auctionTokenData

    } catch (error) {
      console.error('Failed to get token-specific auction data:', error)
      return {}
    }
  }

  /**
   * Get live data for a single auction (both available and amount needed)
   */
  async getSingleAuctionLiveData(
    chainId: number,
    auctionAddress: Address,
    fromToken: Address
  ): Promise<AuctionLiveData> {
    try {
      const auctionCalls: AuctionCall[] = [
        { auctionAddress, fromToken, call: 'available' },
        { auctionAddress, fromToken, call: 'getAmountNeeded' }
      ]

      const results = await this.getAuctionLiveData(chainId, auctionCalls)
      return results[auctionAddress] || { isLoading: false, error: 'No data returned' }

    } catch (error) {
      console.error('Failed to get single auction live data:', error)
      return {
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }
}

// Export singleton instance
export const multicallService = new MulticallService()

// Convenience functions
export const getAuctionLiveData = (chainId: number, auctionCalls: AuctionCall[]) => 
  multicallService.getAuctionLiveData(chainId, auctionCalls)

export const getSingleAuctionLiveData = (chainId: number, auctionAddress: Address, fromToken: Address) =>
  multicallService.getSingleAuctionLiveData(chainId, auctionAddress, fromToken)

export const getTokenSpecificAuctionData = (chainId: number, auctionCalls: AuctionCall[]) =>
  multicallService.getTokenSpecificAuctionData(chainId, auctionCalls)
