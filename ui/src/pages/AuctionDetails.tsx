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
  Gavel,
} from "lucide-react";
import { apiClient } from "../lib/api";
import StatsCard from "../components/StatsCard";
import TakesTable from "../components/TakesTable";
import LoadingSpinner from "../components/LoadingSpinner";
import ChainIcon from "../components/ChainIcon";
import CollapsibleSection from "../components/CollapsibleSection";
import TokensList from "../components/TokensList";
import {
  formatAddress,
  formatTokenAmount,
  formatReadableTokenAmount,
  formatUSD,
  formatTimeAgo,
  formatDuration,
  copyToClipboard,
  getChainInfo,
  cn,
} from "../lib/utils";

const AuctionDetails: React.FC = () => {
  const { chainId, address } = useParams<{ chainId: string; address: string }>();
  const [copiedAddresses, setCopiedAddresses] = useState<Set<string>>(
    new Set()
  );

  // Pagination state for takes
  const [currentPage, setCurrentPage] = useState(1);
  const takesPerPage = 50;

  // Pagination handlers
  const handleNextPage = () => {
    setCurrentPage(prev => prev + 1);
  };

  const handlePrevPage = () => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  };

  // Fetch auction details
  const {
    data: auction,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["auction", chainId, address],
    queryFn: () => apiClient.getAuction(address!, parseInt(chainId!)),
    enabled: !!chainId && !!address,
  });

  // Fetch takes with pagination
  const { data: takes } = useQuery({
    queryKey: ["auctionTakes", chainId, address, currentPage],
    queryFn: () => {
      const offset = (currentPage - 1) * takesPerPage;
      return apiClient.getAuctionTakes(address!, parseInt(chainId!), undefined, takesPerPage, offset);
    },
    enabled: !!chainId && !!address,
  });

  // Pagination state (calculated after takes is available)
  const canGoNext = takes && takes.length === takesPerPage;
  const canGoPrev = currentPage > 1;

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
            Auction Not Found
          </h2>
          <p className="text-gray-500">
            The auction at {formatAddress(address || "", 10)} could not be
            loaded.
          </p>
        </div>
      </div>
    );
  }

  const chainInfo = getChainInfo(auction.chain_id);
  const currentRound = auction.current_round;
  const isActive = currentRound?.is_active || false;
  
  // Calculate time remaining using round_end timestamp, ensuring it floors to 0
  const timeRemaining = currentRound?.round_end 
    ? Math.max(0, currentRound.round_end - Math.floor(Date.now() / 1000))
    : currentRound?.time_remaining || 0;

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="btn btn-secondary btn-sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Link>

          <h1 className="text-2xl font-bold text-gray-100">Auction</h1>
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
          value={auction.activity.total_takes}
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

      {/* Auction Details */}
      <CollapsibleSection
        title="Auction Details"
        icon={Gavel}
        iconColor="text-purple-500"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 justify-items-center">
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Chain</div>
            <div className="flex justify-center">
              <div title={`Chain ID: ${auction.chain_id}`}>
                <ChainIcon chainId={auction.chain_id} size="sm" showName={false} />
              </div>
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Address</div>
            <button
              onClick={() => handleCopy(auction.address)}
              className="font-mono text-sm text-gray-400 hover:text-gray-200 flex items-center space-x-1 transition-colors"
            >
              <span>{formatAddress(auction.address, 4)}</span>
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
                className="p-1 text-gray-400 hover:text-gray-200 transition-colors inline-block mt-1"
              >
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Enabled Tokens</div>
            {auction.from_tokens && auction.from_tokens.length > 0 ? (
              <TokensList
                tokens={auction.from_tokens}
                displayMode="grid"
                maxDisplay={6}
                expandable={true}
                showSearch={auction.from_tokens.length > 20}
                gridColumns={3}
                className="max-w-xs"
                tokenClassName="text-primary-400 font-medium"
                showAddressFeatures={true}
                chainId={auction.chain_id}
              />
            ) : (
              <span className="text-gray-500 text-sm">—</span>
            )}
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Want Token</div>
            <div className="text-yellow-400 font-medium text-sm">
              {auction.want_token?.symbol || "—"}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Decay Rate</div>
            <div className="flex items-center justify-center space-x-1">
              <TrendingDown className="h-3 w-3 text-gray-400" />
              {auction.parameters?.decay_rate !== undefined ? (
                <span className="font-medium text-sm">
                  {(auction.parameters.decay_rate * 100).toFixed(2)}%
                </span>
              ) : auction.parameters?.step_decay_rate ? (
                <span className="font-medium text-sm">
                  {(
                    (1 - parseFloat(auction.parameters.step_decay_rate) / 1e27) *
                    100
                  ).toFixed(2)}
                  %
                </span>
              ) : (
                <span className="text-gray-500">—</span>
              )}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Update Interval</div>
            <div className="flex items-center justify-center space-x-1">
              <Clock className="h-3 w-3 text-gray-400" />
              {auction.parameters?.price_update_interval ? (
                <span className="font-medium text-sm">
                  {auction.parameters.price_update_interval}s
                </span>
              ) : (
                <span className="text-gray-500">—</span>
              )}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Auction Length</div>
            <div className="font-medium text-sm">
              {auction.parameters?.auction_length
                ? `${(auction.parameters.auction_length / 3600).toFixed(1)} hours`
                : "—"}
            </div>
          </div>

          <div className="text-center">
            <div className="text-xs text-gray-500 mb-2">Starting Price</div>
            <div className="font-mono text-sm">
              {auction.parameters?.starting_price
                ? formatReadableTokenAmount(auction.parameters.starting_price, 6)
                : "—"}
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

      {/* Current Round Info */}
      {currentRound && (
        <CollapsibleSection
          title="Current Round"
          icon={() => (
            <div
              className={cn(
                "h-4 w-4 rounded-full",
                isActive ? "bg-success-500 animate-pulse" : "bg-gray-600"
              )}
            />
          )}
          iconColor=""
        >
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 justify-items-center">
            <div className="text-center">
              <div className="text-xs text-gray-500 mb-2">Round ID</div>
              <Link
                to={`/round/${chainId}/${auction.address}/${currentRound.round_id}`}
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
                  {formatReadableTokenAmount(currentRound.current_price, 4)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatUSD(parseFloat(currentRound.current_price) * 1.5)}
                </div>
              </div>
            )}

            {currentRound.initial_available && (
              <div className="text-center">
                <div className="text-xs text-gray-500 mb-2">Starting Amount</div>
                <div className="font-mono text-gray-200 text-sm">
                  {formatTokenAmount(currentRound.initial_available, 18, 2)}
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

            {timeRemaining > 0 && (
              <div className="text-center">
                <div className="text-xs text-gray-500 mb-2">Time Remaining</div>
                <div className="text-success-400 font-medium text-sm">
                  {timeRemaining >= 3600 ? (
                    // >= 1 hour: show hours + minutes
                    `${Math.floor(timeRemaining / 3600)}h ${Math.floor((timeRemaining % 3600) / 60)}m`
                  ) : (
                    // < 1 hour: show minutes + seconds
                    `${Math.floor(timeRemaining / 60)}m ${timeRemaining % 60}s`
                  )}
                </div>
              </div>
            )}

            <div className="text-center">
              <div className="text-xs text-gray-500 mb-2">Sales This Round</div>
              <div className="text-gray-200 font-medium text-sm">
                {currentRound.total_takes}
              </div>
            </div>
          </div>
        </CollapsibleSection>
      )}


      {/* All Takes */}
      {takes && takes.length > 0 && (
        <TakesTable
          takes={takes}
          title="All Takes"
          tokens={tokens?.tokens}
          showRoundInfo={true}
          maxHeight="max-h-[600px]"
          auctionAddress={auction.address}
          // Pagination props
          currentPage={currentPage}
          canGoNext={canGoNext}
          canGoPrev={canGoPrev}
          onNextPage={handleNextPage}
          onPrevPage={handlePrevPage}
        />
      )}

      {/* No Sales State */}
      {(!takes || takes.length === 0) && (
        <div className="card text-center py-8">
          <div className="w-12 h-12 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-3">
            <TrendingDown className="h-6 w-6 text-gray-600" />
          </div>
          <h4 className="text-lg font-medium text-gray-400 mb-1">
            No Takes Yet
          </h4>
          <p className="text-sm text-gray-600">
            This auction hasn't had any takes yet.
          </p>
        </div>
      )}
    </div>
  );
};

export default AuctionDetails;
