import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Clock,
  DollarSign,
  TrendingDown,
  TrendingUp,
  Users,
  ExternalLink,
  Copy,
  Check,
  Activity,
  Home,
} from "lucide-react";
import { apiClient } from "../lib/api";
import StatsCard from "../components/StatsCard";
import SalesTable from "../components/SalesTable";
import LoadingSpinner from "../components/LoadingSpinner";
import ChainIcon from "../components/ChainIcon";
import CollapsibleSection from "../components/CollapsibleSection";
import {
  formatAddress,
  formatTokenAmount,
  formatUSD,
  formatTimeAgo,
  formatDuration,
  copyToClipboard,
  getChainInfo,
  cn,
} from "../lib/utils";

const AuctionDetails: React.FC = () => {
  const { address } = useParams<{ address: string }>();
  const [copiedAddresses, setCopiedAddresses] = useState<Set<string>>(
    new Set()
  );

  // Fetch auction details
  const {
    data: auction,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["auction", address],
    queryFn: () => apiClient.getAuction(address!),
    enabled: !!address,
  });

  // Fetch recent sales
  const { data: sales } = useQuery({
    queryKey: ["auctionSales", address],
    queryFn: () => apiClient.getAuctionSales(address!, undefined, 25),
    enabled: !!address,
  });

  // Fetch tokens for symbol resolution
  const { data: tokens } = useQuery({
    queryKey: ["tokens"],
    queryFn: apiClient.getTokens,
  });

  const handleCopy = async (text: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedAddresses((prev) => new Set(prev).add(text));
      setTimeout(() => {
        setCopiedAddresses((prev) => {
          const newSet = new Set(prev);
          newSet.delete(text);
          return newSet;
        });
      }, 600);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !auction) {
    return (
      <div className="space-y-8">
        <div className="flex items-center space-x-4">
          <Link to="/" className="btn btn-secondary btn-sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>
        </div>

        <div className="card text-center py-12">
          <h2 className="text-xl font-semibold text-gray-300 mb-2">
            Auction House Not Found
          </h2>
          <p className="text-gray-500">
            The auction house at {formatAddress(address || "", 10)} could not be
            loaded.
          </p>
        </div>
      </div>
    );
  }

  const chainInfo = getChainInfo(auction.chain_id);
  const currentRound = auction.current_round;
  const isActive = currentRound?.is_active || false;

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="btn btn-secondary btn-sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>

          <div>
            <div className="flex items-center space-x-3 mb-2">
              <Home className="h-6 w-6 text-primary-500" />
              <h1 className="text-2xl font-bold text-gray-100">
                Auction House
              </h1>
              <ChainIcon chainId={auction.chain_id} size="sm" showName={true} />
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleCopy(auction.address)}
                className="font-mono text-sm text-gray-400 hover:text-gray-200 flex items-center space-x-1 transition-colors"
              >
                <span>{formatAddress(auction.address, 12)}</span>
                {copiedAddresses.has(auction.address) ? (
                  <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>

              {chainInfo.explorer !== "#" && (
                <a
                  href={`${chainInfo.explorer}/address/${auction.address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div
            className={cn(
              "flex items-center space-x-2 px-3 py-1 rounded-full text-sm font-medium",
              isActive
                ? "bg-success-500/20 text-success-400"
                : "bg-gray-700 text-gray-400"
            )}
          >
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                isActive ? "bg-success-500 animate-pulse" : "bg-gray-600"
              )}
            ></div>
            <span>{isActive ? "Active" : "Inactive"}</span>
          </div>
        </div>
      </div>

      {/* Trading Pairs */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Trading Configuration</h3>

        <div className="flex items-center justify-center space-x-8 py-6">
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-2">From Tokens</div>
            <div className="flex flex-wrap gap-2 justify-center">
              {auction.from_tokens.map((token, index) => (
                <span
                  key={token.address}
                  className="inline-flex items-center space-x-1"
                >
                  <span className="text-primary-400 font-medium text-lg">
                    {token.symbol}
                  </span>
                  {index < auction.from_tokens.length - 1 && (
                    <span className="text-gray-500">,</span>
                  )}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center">
            <TrendingDown className="h-8 w-8 text-gray-500" />
          </div>

          <div className="text-center">
            <div className="text-sm text-gray-500 mb-2">Want Token</div>
            <span className="text-yellow-400 font-medium text-lg">
              {auction.want_token.symbol}
            </span>
          </div>
        </div>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Participants"
          value={auction.activity.total_participants}
          icon={Users}
          iconColor="text-blue-500"
        />

        <StatsCard
          title="Total Rounds"
          value={auction.activity.total_rounds}
          icon={TrendingUp}
          iconColor="text-primary-500"
        />

        <StatsCard
          title="Total Sales"
          value={auction.activity.total_sales}
          icon={TrendingDown}
          iconColor="text-primary-500"
        />

        <StatsCard
          title="Total Volume"
          value={formatUSD(auction.activity.total_volume)}
          icon={DollarSign}
          iconColor="text-yellow-500"
        />
      </div>

      {/* Current Round Info */}
      {currentRound && (
        <CollapsibleSection
          title="Current Round"
          icon={Activity}
          iconColor="text-primary-500"
        >
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 justify-items-center">
            <div className="text-center">
              <div className="text-xs text-gray-500 mb-2">Round ID</div>
              <Link
                to={`/round/${auction.address}/${currentRound.round_id}`}
                className="inline-flex items-center space-x-1 text-primary-400 hover:text-primary-300 transition-colors"
              >
                <span className="font-mono font-semibold">
                  R{currentRound.round_id}
                </span>
              </Link>
            </div>

            {currentRound.current_price && (
              <div className="text-center">
                <div className="text-xs text-gray-500 mb-2">Current Price</div>
                <div className="font-mono text-gray-200 text-sm">
                  {formatTokenAmount(currentRound.current_price, 6, 4)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatUSD(parseFloat(currentRound.current_price) * 1.5)}
                </div>
              </div>
            )}

            {currentRound.available_amount && (
              <div className="text-center">
                <div className="text-xs text-gray-500 mb-2">Available</div>
                <div className="font-mono text-gray-200 text-sm">
                  {formatTokenAmount(currentRound.available_amount, 18, 2)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  of {formatTokenAmount(currentRound.initial_available, 18, 2)}
                </div>
              </div>
            )}

            <div className="text-center">
              <div className="text-xs text-gray-500 mb-2">Kicked At</div>
              <div className="text-gray-300 text-sm">
                {formatTimeAgo(
                  new Date(currentRound.kicked_at).getTime() / 1000
                )}
              </div>
            </div>

            {currentRound.time_remaining && (
              <div className="text-center">
                <div className="text-xs text-gray-500 mb-2">Time Remaining</div>
                <div className="text-success-400 font-medium text-sm">
                  {Math.floor(currentRound.time_remaining / 60)}m{" "}
                  {currentRound.time_remaining % 60}s
                </div>
              </div>
            )}

            <div className="text-center">
              <div className="text-xs text-gray-500 mb-2">Sales This Round</div>
              <div className="text-gray-200 font-medium text-sm">
                {currentRound.total_sales}
              </div>
            </div>
          </div>
        </CollapsibleSection>
      )}

      {/* Auction Parameters */}
      <CollapsibleSection
        title="Configuration"
        icon={Activity}
        iconColor="text-purple-500"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 justify-items-center">
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Decay Rate</div>
            <div className="flex items-center justify-center space-x-1">
              <TrendingDown className="h-3 w-3 text-gray-400" />
              <span className="font-medium text-sm">
                {(
                  (1 - parseFloat(auction.parameters.step_decay_rate) / 1e27) *
                  100
                ).toFixed(2)}
                %
              </span>
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Update Interval</div>
            <div className="flex items-center justify-center space-x-1">
              <Clock className="h-3 w-3 text-gray-400" />
              <span className="font-medium text-sm">
                {auction.parameters.price_update_interval}s
              </span>
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Auction Length</div>
            <div className="font-medium text-sm">
              {formatDuration(auction.parameters.auction_length)}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Starting Price</div>
            <div className="font-mono text-sm">
              {formatTokenAmount(auction.parameters.starting_price, 6, 6)}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Deployed</div>
            <div className="text-gray-300 text-sm">
              {formatTimeAgo(new Date(auction.deployed_at).getTime() / 1000)}
            </div>
          </div>

          {auction.last_kicked && (
            <div className="text-center">
              <div className="text-xs text-gray-500 mb-2">Last Kicked</div>
              <div className="text-gray-300 text-sm">
                {formatTimeAgo(new Date(auction.last_kicked).getTime() / 1000)}
              </div>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Recent Sales */}
      {sales && sales.length > 0 && (
        <SalesTable
          sales={sales}
          title="Recent Sales"
          tokens={tokens?.tokens}
          showRoundInfo={true}
          maxHeight="max-h-96"
          auctionAddress={auction.address}
        />
      )}

      {/* No Sales State */}
      {(!sales || sales.length === 0) && (
        <div className="card text-center py-8">
          <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
            <TrendingDown className="h-6 w-6 text-gray-600" />
          </div>
          <h4 className="text-lg font-medium text-gray-400 mb-1">
            No Sales Yet
          </h4>
          <p className="text-sm text-gray-600">
            This auction house hasn't had any sales yet.
          </p>
        </div>
      )}
    </div>
  );
};

export default AuctionDetails;
