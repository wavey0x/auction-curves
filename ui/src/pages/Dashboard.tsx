import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import InternalLink from "../components/InternalLink";
import RoundLink from "../components/RoundLink";
import { useQuery } from "@tanstack/react-query";
import {
  Home,
  TrendingDown,
  TrendingUp,
  Users,
  DollarSign,
  AlertCircle,
  ExternalLink,
  Activity,
  Zap,
  Gavel,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { apiClient } from "../lib/api";
import Pagination from "../components/Pagination";
import StatsCard from "../components/StatsCard";
import TakesTable from "../components/TakesTable";
import StandardTxHashLink from "../components/StandardTxHashLink";
import AddressLink from "../components/AddressLink";
import AuctionsTable from "../components/AuctionsTable";
import StackedProgressMeter from "../components/StackedProgressMeter";
import LoadingSpinner from "../components/LoadingSpinner";
import CollapsibleSection from "../components/CollapsibleSection";
import TokensList from "../components/TokensList";
import TokenPairDisplay from "../components/TokenPairDisplay";
import {
  formatAddress,
  formatTokenAmount,
  formatReadableTokenAmount,
  formatUSD,
  formatTimeAgo,
  getTxLink,
  getChainInfo,
} from "../lib/utils";
import ChainIcon from "../components/ChainIcon";
import type { AuctionTake } from "../types/auction";
import { useUserSettings } from "../context/UserSettingsContext";
import { getAuctionLiveData, type AuctionCall } from "../lib/multicall";

type ViewType = 'active-rounds' | 'takes' | 'all-auctions';

// Pulsing green dot component for active rounds
const PulsingDot: React.FC = () => (
  <div className="relative">
    <div className="h-2 w-2 bg-green-500 rounded-full"></div>
    <div className="absolute top-0 left-0 h-2 w-2 bg-green-500 rounded-full animate-ping"></div>
  </div>
);

const Dashboard: React.FC = () => {
  const { defaultValueDisplay, setDefaultValueDisplay } = useUserSettings();
  const [activeView, setActiveView] = useState<ViewType>('active-rounds');
  const [takesPage, setTakesPage] = useState(1);
  const [takesPerPage] = useState(15);
  const [auctionsPage, setAuctionsPage] = useState(1);
  const [auctionsPerPage] = useState(25);
  const [showUSD, setShowUSD] = useState(defaultValueDisplay === 'usd');

  // Update showUSD when global setting changes
  useEffect(() => {
    setShowUSD(defaultValueDisplay === 'usd');
  }, [defaultValueDisplay]);

  // Function to toggle both local and global setting
  const toggleValueDisplay = () => {
    const newValueDisplay = defaultValueDisplay === 'usd' ? 'token' : 'usd';
    setDefaultValueDisplay(newValueDisplay);
    // setShowUSD will be updated automatically via the useEffect above
  };

  // Fetch data with React Query using new API
  const { data: systemStats, isLoading: statsLoading } = useQuery({
    queryKey: ["systemStats"],
    queryFn: apiClient.getSystemStats,
    // Uses global default: 5 minutes refresh interval
  });

  const { data: auctionsResponse, isLoading: auctionsLoading } = useQuery({
    queryKey: ["auctions", auctionsPage, auctionsPerPage],
    queryFn: () => apiClient.getAuctions({ limit: auctionsPerPage, page: auctionsPage }),
    staleTime: 10000, // Cache for 10 seconds
  });

  const { data: activeAuctionsResponse, isLoading: activeAuctionsLoading } = useQuery({
    queryKey: ["auctions", "active"],
    queryFn: () => apiClient.getAuctions({ status: 'active', limit: 50 }),
    staleTime: 5000, // Cache for 5 seconds - active status changes more frequently
  });

  const { data: tokens } = useQuery({
    queryKey: ["tokens"],
    queryFn: apiClient.getTokens,
    staleTime: 300000, // Cache for 5 minutes - tokens rarely change
  });

  // Stabilize activeAuctions array to prevent hook violations
  const activeAuctions = useMemo(() => {
    return activeAuctionsResponse?.auctions || [];
  }, [activeAuctionsResponse?.auctions]);

  // Get live multicall data for active auctions - using direct hook to avoid filtering issues
  const { data: liveData } = useQuery({
    queryKey: ['active-auctions-live-data', activeAuctions.map(a => a?.address).filter(Boolean).sort()],
    queryFn: async () => {
      if (activeAuctions.length === 0) {
        return {};
      }

      // Skip local Anvil network
      const realNetworkAuctions = activeAuctions.filter(auction => 
        auction && auction.chain_id !== 31337
      );
      
      if (realNetworkAuctions.length === 0) {
        return {};
      }

      // Group auctions by chain for efficient multicall batching
      const auctionsByChain: Record<number, AuctionCall[]> = {};
      
      for (const auction of realNetworkAuctions) {
        if (!auction || !auction.chain_id || !auction.address) {
          continue;
        }
        
        if (!auctionsByChain[auction.chain_id]) {
          auctionsByChain[auction.chain_id] = [];
        }
        
        // Get the specific from_token from the current round (not the first enabled token!)
        const currentRound = auction.current_round;
        const fromTokenAddress = currentRound?.from_token || auction.from_tokens?.[0]?.address;
        
        if (fromTokenAddress) {
          auctionsByChain[auction.chain_id].push(
            {
              auctionAddress: auction.address as any,
              fromToken: fromTokenAddress as any,
              call: 'available'
            },
            {
              auctionAddress: auction.address as any,
              fromToken: fromTokenAddress as any,
              call: 'getAmountNeeded'
            }
          );
        }
      }

      // Execute multicalls for each chain in parallel
      const chainResults = await Promise.all(
        Object.entries(auctionsByChain).map(async ([chainId, calls]) => {
          try {
            const results = await getAuctionLiveData(parseInt(chainId), calls);
            return results;
          } catch (error) {
            console.error(`Failed to fetch live data for chain ${chainId}:`, error);
            return {};
          }
        })
      );

      // Merge results from all chains
      const combinedResults: Record<string, any> = {};
      for (const chainResult of chainResults) {
        Object.assign(combinedResults, chainResult);
      }
      
      return combinedResults;
    },
    enabled: activeAuctions.length > 0,
    refetchInterval: 30000,
    staleTime: 25000,
  });

  // Get takes count for badge (from unified recent takes endpoint)
  const { data: takesCount } = useQuery({
    queryKey: ["recentTakesCount"],
    queryFn: async () => {
      const takes = await apiClient.getRecentTakes(25);
      return takes.length;
    },
    staleTime: 10000,
  });

  // Get recent takes (global, most recent first)
  const { data: allTakes, isLoading: takesLoading } = useQuery({
    queryKey: ["recentTakes"],
    queryFn: async () => apiClient.getRecentTakes(200),
    enabled: activeView === 'takes',
    staleTime: 10000,
  });

  // Paginate the takes
  const totalTakes = allTakes?.length || 0;
  const totalPages = Math.ceil(totalTakes / takesPerPage);
  const startIndex = (takesPage - 1) * takesPerPage;
  const endIndex = startIndex + takesPerPage;
  const recentTakes = allTakes?.slice(startIndex, endIndex) || [];

  // Reset page when switching to takes view
  useEffect(() => {
    if (activeView === 'takes') {
      setTakesPage(1);
    }
  }, [activeView]);

  // Only consider takes loading if we're actually on the takes view
  const isLoading = statsLoading || auctionsLoading || activeAuctionsLoading || 
    (activeView === 'takes' && takesLoading);

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="space-y-6">
          <div className="h-8 bg-gray-800 rounded w-48 animate-pulse"></div>

          <div className="flex flex-wrap justify-center gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <StatsCard
                key={i}
                title="Loading..."
                value="—"
                icon={Home}
                loading={true}
              />
            ))}
          </div>

          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        </div>
      </div>
    );
  }

  const auctions = auctionsResponse?.auctions || [];
  const auctionsTotal = auctionsResponse?.total || 0;

  // Get active rounds from server-filtered active auctions
  const activeRounds = activeAuctions
    .filter((ah) => ah.current_round?.is_active) // Double-check for safety
    .map((ah) => ({
      ...ah.current_round!,
      auction: ah.address,
      chain_id: ah.chain_id,
      from_tokens: ah.from_tokens,
      want_token: ah.want_token,
    }));

  // Get real USD volume from API
  const totalVolumeUSD = systemStats?.total_volume_usd || 0;

  const chainInfo = getChainInfo(31337); // Using Anvil chain

  return (
    <div className="space-y-10">
      {/* Stats Overview */}
      <div className="flex flex-wrap justify-center gap-3">
        <StatsCard
          title="Auctions"
          value={systemStats?.total_auctions || 0}
          icon={Home}
        />

        <StatsCard
          title="Total Volume"
          value={formatUSD(totalVolumeUSD)}
          icon={DollarSign}
        />

        <StatsCard
          title="Total Takes"
          value={systemStats?.total_takes || 0}
          icon={TrendingUp}
        />
      </div>

      {/* Floating Button Group */}
      <div className="relative">
        <div className="flex justify-center mb-6">
          <div className="inline-flex rounded-lg bg-gray-800/50 p-1 backdrop-blur-sm border border-gray-700/50">
            <button
              onClick={() => setActiveView('active-rounds')}
              className={`${
                activeView === 'active-rounds'
                  ? 'bg-primary-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
              } inline-flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 space-x-2`}
            >
              <PulsingDot />
              <span>Active Rounds</span>
              {activeRounds.length > 0 && (
                <span className={`${
                  activeView === 'active-rounds'
                    ? 'bg-white/20 text-white'
                    : 'bg-primary-500/20 text-primary-400'
                } text-xs px-1.5 py-0.5 rounded-full`}>
                  {activeRounds.length}
                </span>
              )}
            </button>
            
            {/* Separator */}
            <div className="w-px bg-gray-600/50 mx-1"></div>
            
            <button
              onClick={() => setActiveView('takes')}
              className={`${
                activeView === 'takes'
                  ? 'bg-primary-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
              } inline-flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 space-x-2`}
            >
              <Activity className="h-4 w-4" />
              <span>Takes</span>
              {takesCount && takesCount > 0 && (
                <span className={`${
                  activeView === 'takes'
                    ? 'bg-white/20 text-white'
                    : 'bg-primary-500/20 text-primary-400'
                } text-xs px-1.5 py-0.5 rounded-full`}>
                  {takesCount}
                </span>
              )}
            </button>
            
            {/* Separator */}
            <div className="w-px bg-gray-600/50 mx-1"></div>
            
            <button
              onClick={() => setActiveView('all-auctions')}
              className={`${
                activeView === 'all-auctions'
                  ? 'bg-primary-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white hover:bg-gray-700/50'
              } inline-flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 space-x-2`}
            >
              <Gavel className="h-4 w-4" />
              <span>Auctions</span>
              {auctionsTotal > 0 && (
                <span className={`${
                  activeView === 'all-auctions'
                    ? 'bg-white/20 text-white'
                    : 'bg-primary-500/20 text-primary-400'
                } text-xs px-1.5 py-0.5 rounded-full`}>
                  {auctionsTotal}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Single Table Area */}
        <div className="card">
          {/* Active Rounds View */}
          {activeView === 'active-rounds' && (
            <>
              {activeRounds.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead className="bg-gray-800">
                      <tr>
                        <th className="text-center w-[22px] min-w-[22px] max-w-[22px] px-0"><span className="sr-only">Chain</span></th>
                        <th className="text-center">Auction</th>
                        <th className="text-center">Round</th>
                        <th className="text-center">Tokens</th>
                        <th className="text-center">Current Price</th>
                        <th className="text-center">Available</th>
                        <th className="text-center">Progress</th>
                        <th className="text-center">Time Left</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeRounds.map((round) => {
                        const wantSymbol = round.want_token.symbol;
                        
                        // Calculate time remaining using round_end timestamp, ensuring it floors to 0
                        const timeRemaining = round.round_end 
                          ? Math.max(0, round.round_end - Math.floor(Date.now() / 1000))
                          : round.time_remaining || 0;

                        // Calculate time progress with fallbacks
                        const calculateTimeProgress = () => {
                          // If we have proper start and end times, use them
                          if (round.round_start && round.round_end) {
                            const totalDuration = round.round_end - round.round_start
                            const elapsed = Math.floor(Date.now() / 1000) - round.round_start
                            
                            if (totalDuration <= 0) return 100
                            
                            return Math.min(100, Math.max(0, (elapsed / totalDuration) * 100))
                          }
                          
                          // Fallback: use seconds_elapsed and time_remaining if available
                          if (round.seconds_elapsed && timeRemaining > 0) {
                            const totalTime = round.seconds_elapsed + timeRemaining
                            return Math.min(100, Math.max(0, (round.seconds_elapsed / totalTime) * 100))
                          }
                          
                          // Final fallback: assume some progress if active, complete if not
                          return round.is_active ? 25 : 100
                        };
                        
                        const timeProgress = calculateTimeProgress();

                        return (
                          <tr
                            key={`${round.auction}-${round.round_id}`}
                            className="group"
                          >
                            <td className="w-[22px] min-w-[22px] max-w-[22px] px-0 text-center">
                              <div className="flex justify-center">
                                <ChainIcon
                                  chainId={round.chain_id}
                                  size="xs"
                                  showName={false}
                                />
                              </div>
                            </td>

                            <td>
                              <InternalLink
                                to={`/auction/${round.chain_id}/${round.auction}`}
                                variant="address"
                                className="font-mono text-sm"
                                address={round.auction}
                                chainId={round.chain_id}
                              >
                                {formatAddress(round.auction)}
                              </InternalLink>
                            </td>

                            <td>
                              <div className="flex justify-center">
                                <RoundLink
                                  chainId={round.chain_id}
                                  auctionAddress={round.auction}
                                  roundId={round.round_id}
                                />
                              </div>
                            </td>

                            <td>
                              <TokenPairDisplay
                                fromToken={(() => {
                                  // Find the specific token for this round if from_token field exists
                                  if (round.from_token && round.from_tokens) {
                                    const specificToken = round.from_tokens.find(t => 
                                      t.address.toLowerCase() === round.from_token.toLowerCase()
                                    );
                                    return specificToken?.symbol || round.from_token.slice(0,6) + "…" + round.from_token.slice(-4);
                                  }
                                  // Fallback to first token if no specific from_token field
                                  return round.from_tokens?.[0]?.symbol || "Token";
                                })()}
                                toToken={wantSymbol}
                              />
                            </td>

                            <td>
                              {(() => {
                                const auctionLiveData = liveData?.[round.auction];
                                const currentPrice = auctionLiveData?.amountNeeded;
                                
                                if (currentPrice !== undefined && currentPrice !== null) {
                                  // Format the live price data (including 0 values)
                                  const priceValue = Number(currentPrice) / Math.pow(10, 18);
                                  return (
                                    <div className="text-sm">
                                      <div className="font-mono text-gray-200">
                                        {formatReadableTokenAmount(priceValue.toString(), 3)}
                                      </div>
                                      <div className="text-xs text-gray-500">
                                        {formatUSD(priceValue * 1.5)}
                                      </div>
                                    </div>
                                  );
                                } else if (round.current_price) {
                                  // Fallback to database price if available
                                  return (
                                    <div className="text-sm">
                                      <div className="font-mono text-gray-200">
                                        {formatReadableTokenAmount(round.current_price, 3)}
                                      </div>
                                      <div className="text-xs text-gray-500">
                                        {formatUSD(parseFloat(round.current_price) * 1.5)}
                                      </div>
                                    </div>
                                  );
                                } else {
                                  console.log(`❌ No price data for ${round.auction}`);
                                  return <span className="text-gray-500 text-sm">—</span>;
                                }
                              })()}
                            </td>

                            <td>
                              {(() => {
                                const auctionLiveData = liveData?.[round.auction];
                                const availableAmount = auctionLiveData?.available;
                                
                                // Debug logging
                                console.log(`📦 Available data for auction ${round.auction}:`, {
                                  hasLiveData: !!auctionLiveData,
                                  availableAmount,
                                  availableAmountType: typeof availableAmount,
                                  availableAmountString: availableAmount?.toString(),
                                  fallbackAmount: round.available_amount
                                });
                                
                                if (availableAmount !== undefined && availableAmount !== null) {
                                  // Format the live available data (including 0 values)
                                  const availableValue = Number(availableAmount) / Math.pow(10, 18);
                                  console.log(`✅ Using live available for ${round.auction}: ${availableValue}`);
                                  
                                  // Get the correct token symbol for this round
                                  const specificToken = round.from_tokens?.find(t => 
                                    t.address.toLowerCase() === round.from_token?.toLowerCase()
                                  );
                                  const tokenSymbol = specificToken?.symbol || "Token";
                                  
                                  return (
                                    <div className="text-sm">
                                      <div className="font-mono text-gray-200">
                                        {formatTokenAmount(availableValue.toString(), 0, 2)}
                                      </div>
                                      <div className="text-xs text-gray-500">
                                        {tokenSymbol}
                                      </div>
                                    </div>
                                  );
                                } else if (round.available_amount) {
                                  // Fallback to database amount if available
                                  console.log(`📊 Using database available for ${round.auction}: ${round.available_amount}`);
                                  
                                  // Get the correct token symbol for this round
                                  const specificToken = round.from_tokens?.find(t => 
                                    t.address.toLowerCase() === round.from_token?.toLowerCase()
                                  );
                                  const tokenSymbol = specificToken?.symbol || "Token";
                                  
                                  return (
                                    <div className="text-sm">
                                      <div className="font-mono text-gray-200">
                                        {formatTokenAmount(round.available_amount, 18, 2)}
                                      </div>
                                      <div className="text-xs text-gray-500">
                                        {tokenSymbol}
                                      </div>
                                    </div>
                                  );
                                } else {
                                  console.log(`❌ No available data for ${round.auction}`);
                                  return <span className="text-gray-500 text-sm">—</span>;
                                }
                              })()}
                            </td>

                            <td>
                              {/* Always show progress bar for active rounds */}
                              <div className="min-w-[120px]">
                                <StackedProgressMeter
                                  timeProgress={timeProgress}
                                  amountProgress={round.progress_percentage || 0}
                                  timeRemaining={timeRemaining}
                                  totalTakes={round.total_takes || 0}
                                  size="sm"
                                />
                              </div>
                            </td>

                            <td>
                              {timeRemaining > 0 ? (
                                <div>
                                  <div className="font-medium text-white text-base">
                                    {timeRemaining > 3600 ? (
                                      `${Math.floor(timeRemaining / 3600)}h ${Math.floor((timeRemaining % 3600) / 60)}m`
                                    ) : (
                                      `${Math.floor(timeRemaining / 60)}m ${timeRemaining % 60}s`
                                    )}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {round.seconds_elapsed !== undefined && round.seconds_elapsed !== null ? (
                                      round.seconds_elapsed > 3600 ? (
                                        `${Math.floor(round.seconds_elapsed / 3600)}h ${Math.floor((round.seconds_elapsed % 3600) / 60)}m elapsed`
                                      ) : (
                                        `${Math.floor(round.seconds_elapsed / 60)}m ${round.seconds_elapsed % 60}s elapsed`
                                      )
                                    ) : round.round_start ? (
                                      (() => {
                                        const elapsed = Math.floor(Date.now() / 1000) - round.round_start;
                                        return elapsed > 3600 ? (
                                          `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m elapsed`
                                        ) : (
                                          `${Math.floor(elapsed / 60)}m ${elapsed % 60}s elapsed`
                                        );
                                      })()
                                    ) : (
                                      '0s elapsed'
                                    )}
                                  </div>
                                </div>
                              ) : (
                                <span className="text-gray-500 text-sm">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <TrendingUp className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Active Rounds</h3>
                  <p className="text-sm">No auction rounds are currently active</p>
                </div>
              )}
            </>
          )}

          {/* Takes View */}
          {activeView === 'takes' && (
            <>
              {recentTakes && recentTakes.length > 0 ? (
                <>
                  <div className="card overflow-visible">
                    <table className="w-full border-collapse">
                      <thead className="bg-gray-800">
                        <tr>
                          <th className="border-b border-gray-700 px-0 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider w-[22px] min-w-[22px] max-w-[22px]"><span className="sr-only">Chain</span></th>
                          <th className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider">Auction</th>
                          <th className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider">Round</th>
                          <th className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider w-28 md:w-36">Tokens</th>
                          <th 
                            className="border-b border-gray-700 px-2 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-700/50 transition-colors w-24 md:w-28"
                            onClick={toggleValueDisplay}
                            title="Click to toggle between token and USD values"
                          >
                            Amount {showUSD ? '($)' : '(T)'}
                          </th>
                          <th 
                            className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-700/50 transition-colors"
                            onClick={toggleValueDisplay}
                            title="Click to toggle between token and USD values"
                          >
                            Price {showUSD ? '($)' : '(T)'}
                          </th>
                          <th className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider">Taker</th>
                          <th className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider">Transaction</th>
                          <th className="border-b border-gray-700 px-3 py-1.5 text-center text-xs font-medium text-gray-400 uppercase tracking-wider w-24 md:w-28 whitespace-nowrap">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentTakes.map((take, index) => (
                          <tr key={take.take_id || `take-${index}`} className="group hover:bg-gray-800/50">
                            <td className="border-b border-gray-800 px-0 py-1.5 text-sm text-gray-300 w-[22px] min-w-[22px] max-w-[22px] text-center">
                              <div className="flex justify-center">
                                <ChainIcon
                                  chainId={take.chain_id}
                                  size="xs"
                                  showName={false}
                                />
                              </div>
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300">
                              <AddressLink
                                address={take.auction}
                                chainId={take.chain_id}
                                type="auction"
                                length={5}
                                className="text-gray-300"
                              />
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300">
                              <div className="flex justify-center">
                                <RoundLink
                                  chainId={take.chain_id}
                                  auctionAddress={take.auction}
                                  roundId={take.round_id}
                                />
                              </div>
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300 w-28 md:w-36 max-w-[9rem] md:max-w-[14rem]">
                              <div className="flex flex-col items-start">
                                <div className="font-medium text-sm text-gray-300 flex items-center space-x-1">
                                  <span>{take.from_token_symbol || 'Token'}</span>
                                  <span className="text-xs text-gray-500">→</span>
                                </div>
                                <div className="font-bold text-sm text-white">
                                  {take.to_token_symbol || 'USDC'}
                                </div>
                              </div>
                            </td>

                            <td className="border-b border-gray-800 px-2 py-1.5 text-sm text-gray-300 whitespace-nowrap w-24 md:w-28">
                              <div className="text-sm">
                                <div className="font-medium text-gray-200">
                                  {showUSD ? (
                                    take.amount_taken_usd ? (
                                      formatUSD(parseFloat(take.amount_taken_usd))
                                    ) : (
                                      <span className="text-gray-500">—</span>
                                    )
                                  ) : (
                                    formatReadableTokenAmount(take.amount_taken, 3)
                                  )}
                                </div>
                                <div className="text-xs text-gray-500 truncate">{take.from_token_symbol || 'token'}</div>
                              </div>
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300">
                              <div className="text-sm">
                                <div className="font-medium text-gray-200">
                                  {showUSD ? (
                                    take.amount_paid_usd && take.amount_taken ? (
                                      formatUSD(parseFloat(take.amount_paid_usd) / parseFloat(take.amount_taken))
                                    ) : (
                                      <span className="text-gray-500">—</span>
                                    )
                                  ) : (
                                    formatReadableTokenAmount(take.price, 4)
                                  )}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {showUSD ? 
                                    `per ${take.from_token_symbol || 'token'}` : 
                                    `${take.to_token_symbol || 'token'} per ${take.from_token_symbol || 'token'}`
                                  }
                                </div>
                              </div>
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300">
                              <AddressLink
                                address={take.taker}
                                chainId={take.chain_id}
                                type="address"
                                length={5}
                                className="text-gray-400"
                              />
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300">
                              <div className="flex justify-center">
                                <StandardTxHashLink
                                  txHash={take.tx_hash}
                                  chainId={take.chain_id}
                                />
                              </div>
                            </td>

                            <td className="border-b border-gray-800 px-3 py-1.5 text-sm text-gray-300 w-24 md:w-28 whitespace-nowrap text-center">
                              <span 
                                className="text-sm text-gray-400 cursor-help"
                                title={new Date(take.timestamp).toLocaleString()}
                              >
                                {formatTimeAgo(take.timestamp)}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Unified Pagination */}
                  {totalPages > 1 && (
                    <Pagination
                      currentPage={takesPage}
                      canGoPrev={takesPage > 1}
                      canGoNext={takesPage < totalPages}
                      onPrev={() => setTakesPage(Math.max(1, takesPage - 1))}
                      onNext={() => setTakesPage(Math.min(totalPages, takesPage + 1))}
                      summaryText={`Showing ${startIndex + 1}-${Math.min(endIndex, totalTakes)} of ${totalTakes} takes`}
                      totalPages={totalPages}
                    />
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Activity className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Takes</h3>
                  <p className="text-sm">No takes have been recorded recently</p>
                </div>
              )}
            </>
          )}

          {/* All Auctions View */}
          {activeView === 'all-auctions' && (
            <>
              {auctions && auctions.length > 0 ? (
                <>
                  <AuctionsTable auctions={auctions} />
                  {(auctionsResponse?.total || 0) > (auctionsResponse?.per_page || auctionsPerPage) && (
                    <Pagination
                      currentPage={auctionsResponse?.page || auctionsPage}
                      canGoPrev={(auctionsResponse?.page || auctionsPage) > 1}
                      canGoNext={!!auctionsResponse?.has_next}
                      onPrev={() => setAuctionsPage(Math.max(1, (auctionsResponse?.page || auctionsPage) - 1))}
                      onNext={() => setAuctionsPage((auctionsResponse?.page || auctionsPage) + 1)}
                      summaryText={`Showing ${(auctionsResponse!.page - 1) * auctionsResponse!.per_page + 1}-${Math.min(auctionsResponse!.page * auctionsResponse!.per_page, auctionsResponse!.total)} of ${auctionsResponse!.total} auctions`}
                      totalPages={Math.ceil((auctionsResponse?.total || 0) / (auctionsResponse?.per_page || auctionsPerPage))}
                    />
                  )}
                </>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <Home className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Auctions Found</h3>
                  <p className="text-sm">Deploy some auctions to see them appear here</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

    </div>
  );
};

export default Dashboard;
