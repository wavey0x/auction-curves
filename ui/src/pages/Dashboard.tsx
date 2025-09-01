import React, { useState } from "react";
import { Link } from "react-router-dom";
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
} from "lucide-react";
import { apiClient } from "../lib/api";
import StatsCard from "../components/StatsCard";
import TakesTable from "../components/TakesTable";
import AuctionsTable from "../components/AuctionsTable";
import StackedProgressMeter from "../components/StackedProgressMeter";
import LoadingSpinner from "../components/LoadingSpinner";
import CollapsibleSection from "../components/CollapsibleSection";
import TokensList from "../components/TokensList";
import {
  formatAddress,
  formatTokenAmount,
  formatUSD,
  formatTimeAgo,
  getTxLink,
  getChainInfo,
} from "../lib/utils";
import ChainIcon from "../components/ChainIcon";

type ViewType = 'active-rounds' | 'takes' | 'all-auctions';

// Pulsing green dot component for active rounds
const PulsingDot: React.FC = () => (
  <div className="relative">
    <div className="h-2 w-2 bg-green-500 rounded-full"></div>
    <div className="absolute top-0 left-0 h-2 w-2 bg-green-500 rounded-full animate-ping"></div>
  </div>
);

const Dashboard: React.FC = () => {
  const [activeView, setActiveView] = useState<ViewType>('active-rounds');

  // Fetch data with React Query using new API
  const { data: systemStats, isLoading: statsLoading } = useQuery({
    queryKey: ["systemStats"],
    queryFn: apiClient.getSystemStats,
    staleTime: 30000, // Cache for 30 seconds - stats don't change frequently
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const { data: auctionsResponse, isLoading: auctionsLoading } = useQuery({
    queryKey: ["auctions"],
    queryFn: () => apiClient.getAuctions({ limit: 50 }),
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

  // Get takes count for badge (always load for badge display)
  const { data: takesCount } = useQuery({
    queryKey: ["recentTakesCount"],
    queryFn: async () => {
      const activeAuctions = activeAuctionsResponse?.auctions || [];
      let totalCount = 0;

      // Get count from first few active auctions (already filtered server-side)
      const limitedActiveAuctions = activeAuctions.slice(0, 5);

      for (const auction of limitedActiveAuctions) {
        try {
          const takes = await apiClient.getAuctionTakes(
            auction.address,
            auction.chain_id,
            undefined,
            5
          );
          totalCount += takes.length;
        } catch (error) {
          console.warn(`Failed to fetch takes count for ${auction.address}:`, error);
        }
      }

      return Math.min(totalCount, 25); // Cap at 25 to match full query
    },
    enabled: !!activeAuctionsResponse?.auctions?.length,
    staleTime: 10000, // Cache for 10 seconds
  });

  // Get recent takes activity from auctions (only load when takes view is selected)
  const { data: recentTakes, isLoading: takesLoading } = useQuery({
    queryKey: ["recentTakes"],
    queryFn: async () => {
      const activeAuctions = activeAuctionsResponse?.auctions || [];
      const allTakes: AuctionSale[] = [];

      // Get takes from first few active auctions (already filtered server-side)
      const limitedActiveAuctions = activeAuctions.slice(0, 5);

      for (const auction of limitedActiveAuctions) {
        try {
          const takes = await apiClient.getAuctionTakes(
            auction.address,
            auction.chain_id,
            undefined,
            5
          );
          allTakes.push(...takes);
        } catch (error) {
          console.warn(`Failed to fetch takes for ${auction.address}:`, error);
        }
      }

      // Sort by timestamp and take most recent
      return allTakes
        .sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        )
        .slice(0, 25);
    },
    enabled: !!activeAuctionsResponse?.auctions?.length && activeView === 'takes',
    staleTime: 10000, // Cache for 10 seconds to prevent redundant fetches
  });

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
  const activeAuctions = activeAuctionsResponse?.auctions || [];

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

  const totalVolume = auctions.reduce((sum, ah) => {
    return (
      sum +
      (parseFloat(ah.current_round?.available_amount || "0") / 10 ** 18) * 1000
    ); // Mock volume calc
  }, 0);

  const chainInfo = getChainInfo(31337); // Using Anvil chain

  return (
    <div className="space-y-10">
      {/* Stats Overview */}
      <div className="flex flex-wrap justify-center gap-3">
        <StatsCard
          title="Active Rounds"
          value={activeRounds.length}
          icon={Activity}
        />

        <StatsCard
          title="Auctions"
          value={systemStats?.total_auctions || 0}
          icon={Home}
        />

        <StatsCard
          title="Total Volume"
          value={`$${Math.round(totalVolume).toLocaleString()}`}
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
              {auctions && auctions.length > 0 && (
                <span className={`${
                  activeView === 'all-auctions'
                    ? 'bg-white/20 text-white'
                    : 'bg-primary-500/20 text-primary-400'
                } text-xs px-1.5 py-0.5 rounded-full`}>
                  {auctions.length}
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
                    <thead className="bg-gray-800/50">
                      <tr>
                        <th className="text-center">Round</th>
                        <th className="text-center w-16">Chain</th>
                        <th className="text-center">Auction</th>
                        <th className="text-center">From → Want</th>
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

                        return (
                          <tr
                            key={`${round.auction}-${round.round_id}`}
                            className="group"
                          >
                            <td>
                              <Link
                                to={`/round/${round.chain_id}/${round.auction}/${round.round_id}`}
                                className="inline-flex items-center space-x-2 px-3 py-1.5 hover:bg-gray-800/30 rounded-lg transition-all duration-200 group"
                              >
                                <span className="font-mono text-base font-semibold text-gray-300 group-hover:text-primary-300">
                                  R{round.round_id}
                                </span>
                              </Link>
                            </td>

                            <td className="w-16 text-center">
                              <div className="flex justify-center">
                                <ChainIcon
                                  chainId={round.chain_id}
                                  size="sm"
                                  showName={false}
                                />
                              </div>
                            </td>

                            <td>
                              <Link
                                to={`/auction/${round.chain_id}/${round.auction}`}
                                className="font-mono text-sm text-gray-300 hover:text-primary-300 transition-colors"
                              >
                                {formatAddress(round.auction)}
                              </Link>
                            </td>

                            <td>
                              <div className="flex items-center space-x-2">
                                <TokensList 
                                  tokens={round.from_tokens}
                                  maxDisplay={2}
                                  tokenClassName="font-medium text-gray-200 text-sm"
                                />
                                <span className="text-gray-500">→</span>
                                <span className="font-medium text-yellow-400 text-sm">
                                  {wantSymbol}
                                </span>
                              </div>
                            </td>

                            <td>
                              {round.current_price ? (
                                <div className="text-sm">
                                  <div className="font-mono text-gray-200">
                                    {formatTokenAmount(round.current_price, 6, 3)}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {formatUSD(parseFloat(round.current_price) * 1.5)}
                                  </div>
                                </div>
                              ) : (
                                <span className="text-gray-500 text-sm">—</span>
                              )}
                            </td>

                            <td>
                              {round.available_amount ? (
                                <div className="text-sm">
                                  <div className="font-mono text-gray-200">
                                    {formatTokenAmount(round.available_amount, 18, 2)}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    of{" "}
                                    {formatTokenAmount(
                                      round.initial_available,
                                      18,
                                      2
                                    )}
                                  </div>
                                </div>
                              ) : (
                                <span className="text-gray-500 text-sm">—</span>
                              )}
                            </td>

                            <td>
                              {round.progress_percentage !== undefined &&
                              timeRemaining > 0 ? (
                                <div className="min-w-[120px]">
                                  <StackedProgressMeter
                                    timeProgress={
                                      (round.seconds_elapsed /
                                        (round.seconds_elapsed +
                                          timeRemaining)) *
                                      100
                                    }
                                    amountProgress={round.progress_percentage}
                                    timeRemaining={timeRemaining}
                                    totalTakes={round.total_takes}
                                    size="sm"
                                  />
                                </div>
                              ) : round.progress_percentage !== undefined ? (
                                <div className="text-sm">
                                  <div className="flex items-center space-x-2 mb-1">
                                    <span className="text-gray-300">
                                      {round.progress_percentage.toFixed(0)}%
                                    </span>
                                    <span className="text-xs text-gray-500">
                                      ({round.total_takes} takes)
                                    </span>
                                  </div>
                                  <div className="w-full bg-gray-700 rounded-full h-1">
                                    <div
                                      className="bg-primary-500 h-1 rounded-full"
                                      style={{
                                        width: `${round.progress_percentage}%`,
                                      }}
                                    ></div>
                                  </div>
                                </div>
                              ) : (
                                <span className="text-gray-500 text-sm">—</span>
                              )}
                            </td>

                            <td>
                              {timeRemaining > 0 ? (
                                <div className="text-sm">
                                  <div className="font-medium text-success-400">
                                    {Math.floor(timeRemaining / 60)}m{" "}
                                    {timeRemaining % 60}s
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {Math.floor(round.seconds_elapsed / 60)}m elapsed
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
                <div className="overflow-y-auto max-h-[600px]">
                  <table className="table">
                    <thead className="bg-gray-800/50 sticky top-0">
                      <tr>
                        <th className="text-center">Transaction</th>
                        <th className="text-center">Sale</th>
                        <th className="text-center w-16">Chain</th>
                        <th className="text-center">Auction</th>
                        <th className="text-center">Tokens</th>
                        <th className="text-center">Amount</th>
                        <th className="text-center">Price</th>
                        <th className="text-center">Taker</th>
                        <th className="text-center">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentTakes.map((sale, index) => (
                        <tr key={sale.take_id || `take-${index}`} className="group">
                          <td>
                            <div className="flex items-center space-x-2">
                              {getChainInfo(sale.chain_id).explorer !== "#" ? (
                                <a
                                  href={getTxLink(sale.tx_hash, sale.chain_id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors flex items-center space-x-1"
                                  title="View transaction"
                                >
                                  <span>{formatAddress(sale.tx_hash)}</span>
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              ) : (
                                <span className="font-mono text-sm text-gray-400">
                                  {formatAddress(sale.tx_hash)}
                                </span>
                              )}
                            </div>
                          </td>

                          <td>
                            <div className="flex items-center space-x-2">
                              <TrendingDown className="h-4 w-4 text-primary-500" />
                              <div className="text-sm">
                                <div className="font-mono text-xs text-gray-500">
                                  R{sale.round_id}T{sale.take_seq}
                                </div>
                              </div>
                            </div>
                          </td>

                          <td className="w-16 text-center">
                            <div className="flex justify-center">
                              <ChainIcon
                                chainId={sale.chain_id}
                                size="sm"
                                showName={false}
                              />
                            </div>
                          </td>

                          <td>
                            <Link
                              to={`/auction/${sale.chain_id}/${sale.auction}`}
                              className="font-mono text-sm text-gray-300 hover:text-primary-300 transition-colors"
                            >
                              {formatAddress(sale.auction)}
                            </Link>
                          </td>

                          <td>
                            <div className="space-y-1">
                              <div className="flex items-center space-x-1 text-sm">
                                <span className="font-medium text-gray-300">
                                  Token
                                </span>
                                <span className="text-gray-500">→</span>
                                <span className="font-medium text-yellow-400">
                                  USDC
                                </span>
                              </div>
                            </div>
                          </td>

                          <td>
                            <div className="text-sm font-medium text-gray-200">
                              {formatTokenAmount(sale.amount_taken, 18, 3)}
                            </div>
                          </td>

                          <td>
                            <div className="text-sm">
                              <div className="font-medium text-gray-200">
                                {formatTokenAmount(sale.price, 6, 4)}
                              </div>
                              <div className="text-xs text-gray-500">
                                {formatUSD(parseFloat(sale.price) * 1.5)}
                              </div>
                            </div>
                          </td>

                          <td>
                            <span className="font-mono text-sm text-gray-400">
                              {formatAddress(sale.taker)}
                            </span>
                          </td>

                          <td>
                            <span className="text-sm text-gray-400">
                              {formatTimeAgo(sale.timestamp)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
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
                <AuctionsTable auctions={auctions} />
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
