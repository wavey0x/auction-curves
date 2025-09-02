import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
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
import RoundsTable from "../components/RoundsTable";
import IdentityRow from "../components/IdentityRow";
import KeyValueGrid from "../components/KeyValueGrid";
import MetaBadges from "../components/MetaBadges";
import CompactTokensDisplay from "../components/CompactTokensDisplay";
import ExpandedTokensList from "../components/ExpandedTokensList";
import TokenWithAddress from "../components/TokenWithAddress";
import BackButton from "../components/BackButton";
import {
  formatAddress,
  formatTokenAmount,
  formatReadableTokenAmount,
  formatUSD,
  formatTimeAgo,
  formatDuration,
  copyToClipboard,
  getChainInfo,
} from "../lib/utils";
import InternalLink from "../components/InternalLink";

const AuctionDetails: React.FC = () => {
  const { chainId, address } = useParams<{ chainId: string; address: string }>();
  const [copiedAddresses, setCopiedAddresses] = useState<Set<string>>(
    new Set()
  );

  // Pagination state for takes
  const [currentPage, setCurrentPage] = useState(1);
  const takesPerPage = 5;

  // Pagination state for rounds
  const [currentRoundsPage, setCurrentRoundsPage] = useState(1);
  const roundsPerPage = 5;

  // Token expansion state
  const [tokensExpanded, setTokensExpanded] = useState(false);

  // Pagination handlers for takes
  const handleNextPage = () => {
    setCurrentPage(prev => prev + 1);
  };

  const handlePrevPage = () => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  };

  // Pagination handlers for rounds
  const handleNextRoundsPage = () => {
    setCurrentRoundsPage(prev => prev + 1);
  };

  const handlePrevRoundsPage = () => {
    setCurrentRoundsPage(prev => Math.max(1, prev - 1));
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
  const { data: takesResponse } = useQuery({
    queryKey: ["auctionTakes", chainId, address, currentPage],
    queryFn: () => {
      const offset = (currentPage - 1) * takesPerPage;
      return apiClient.getAuctionTakes(address!, parseInt(chainId!), undefined, takesPerPage, offset);
    },
    enabled: !!chainId && !!address,
  });

  // Extract takes data and pagination info
  const takes = takesResponse?.takes || [];
  const totalTakes = takesResponse?.total || 0;
  const totalTakesPages = takesResponse?.total_pages || 1;
  
  // Pagination state for takes (calculated from API response)
  const canGoNext = takesResponse ? currentPage < totalTakesPages : false;
  const canGoPrev = currentPage > 1;

  // Fetch tokens for symbol resolution
  const { data: tokens } = useQuery({
    queryKey: ["tokens"],
    queryFn: apiClient.getTokens,
  });

  // Fetch all rounds across all from_tokens, merge and sort
  const { data: allRounds } = useQuery({
    queryKey: ["auctionRoundsAll", chainId, address, auction?.from_tokens?.map(t => t.address).join(",")],
    queryFn: async () => {
      if (!auction?.from_tokens?.length) return [] as any[];
      const chain = parseInt(chainId!);
      const results = await Promise.all(
        auction.from_tokens.map(ft => 
          apiClient.getAuctionRounds(address!, chain, ft.address)
            .then(r => ({ rounds: r.rounds || [], from: ft.address }))
        )
      );
      const merged = results.flatMap(({ rounds, from }) => 
        rounds.map(r => ({ ...r, from_token: from }))
      );
      return merged.sort((a, b) => new Date(b.kicked_at).getTime() - new Date(a.kicked_at).getTime());
    },
    enabled: !!auction && !!chainId && !!address,
    staleTime: 10000,
  });

  // Pagination state for rounds (calculated after allRounds is available)
  const totalRounds = allRounds?.length || 0;
  const totalRoundsPages = Math.ceil(totalRounds / roundsPerPage);
  const startRoundIndex = (currentRoundsPage - 1) * roundsPerPage;
  const endRoundIndex = startRoundIndex + roundsPerPage;
  const paginatedRounds = allRounds?.slice(startRoundIndex, endRoundIndex) || [];
  const canGoNextRounds = endRoundIndex < totalRounds;
  const canGoPrevRounds = currentRoundsPage > 1;

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
          <BackButton />
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

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <BackButton />

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
          title="Total Takes"
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
      <CollapsibleSection title="Auction Details" icon={Gavel} iconColor="text-purple-500">
        <div className="space-y-6">
          {/* Identity Section */}
          <div>
            <IdentityRow address={auction.address} chainId={auction.chain_id} />
          </div>

          {/* Configuration Grid */}
          <div>
            <KeyValueGrid
              columns={3}
              items={[
                {
                  label: 'Want Token',
                  value: auction.want_token ? (
                    <TokenWithAddress
                      token={auction.want_token}
                      chainId={auction.chain_id}
                      className="text-white font-medium hover:text-primary-300"
                      showSymbolOnly={true}
                    />
                  ) : (
                    <span className="text-gray-500">—</span>
                  ),
                },
                { 
                  label: 'Interval / Decay', 
                  value: `${auction.parameters?.price_update_interval ? `${auction.parameters.price_update_interval}s` : '—'} / ${
                    auction.parameters?.decay_rate !== undefined
                      ? `${(auction.parameters.decay_rate * 100).toFixed(2)}%`
                      : auction.parameters?.step_decay_rate
                      ? `${((1 - parseFloat(auction.parameters.step_decay_rate) / 1e27) * 100).toFixed(2)}%`
                      : '—'
                  }` 
                },
                { label: 'Auction Length', value: auction.parameters?.auction_length ? `${(auction.parameters.auction_length / 3600).toFixed(1)} h` : '—' },
                { label: 'Starting Price', value: auction.parameters?.starting_price ? <span className="font-mono">{formatReadableTokenAmount(auction.parameters.starting_price, 6)}</span> : '—' },
                ...(auction.last_kicked ? [{ label: 'Last Kicked', value: <span title={new Date(auction.last_kicked).toLocaleString()}>{formatTimeAgo(new Date(auction.last_kicked).getTime()/1000)}</span> }] : [] as any),
                {
                  label: 'Enabled Tokens',
                  value: (
                    <CompactTokensDisplay
                      tokens={auction.from_tokens || []}
                      maxDisplay={2}
                      isExpanded={tokensExpanded}
                      onToggle={() => setTokensExpanded(!tokensExpanded)}
                      chainId={auction.chain_id}
                    />
                  ),
                  expandable: true,
                  isExpanded: tokensExpanded,
                  expandedContent: tokensExpanded && auction.from_tokens && auction.from_tokens.length > 0 ? (
                    <ExpandedTokensList
                      tokens={auction.from_tokens}
                      chainId={auction.chain_id}
                    />
                  ) : null,
                },
              ]}
            />
          </div>

          {/* Activity Summary */}
          <div>
            <MetaBadges
              items={[
                { label: 'Deployed', value: formatTimeAgo(new Date(auction.deployed_at).getTime()/1000), icon: Clock },
                { label: 'Participants', value: auction.activity.total_participants || 0, icon: Users },
                { label: 'Volume', value: formatUSD(auction.activity.total_volume) },
              ]}
            />
          </div>
        </div>
      </CollapsibleSection>

      {/* Current Round section removed per request */}


      {/* Rounds History */}
      {allRounds && allRounds.length > 0 && (
        <CollapsibleSection title="Rounds History" icon={TrendingUp} iconColor="text-primary-500" seamless={true}>
          <RoundsTable
            rounds={paginatedRounds as any}
            auctionAddress={auction.address}
            chainId={parseInt(chainId!)}
            fromTokens={auction.from_tokens}
            wantToken={auction.want_token}
            title=""
            currentPage={currentRoundsPage}
            canGoNext={canGoNextRounds}
            canGoPrev={canGoPrevRounds}
            onNextPage={handleNextRoundsPage}
            onPrevPage={handlePrevRoundsPage}
            totalPages={totalRoundsPages}
          />
        </CollapsibleSection>
      )}

      {/* All Takes */}
      {takes && takes.length > 0 && (
        <CollapsibleSection title="All Takes" icon={Activity} iconColor="text-green-500" seamless={true}>
          <TakesTable
            takes={takes}
            title=""
            tokens={tokens?.tokens}
            showRoundInfo={true}
            maxHeight="max-h-[600px]"
            auctionAddress={auction.address}
            hideAuctionColumn={true}
            // Pagination props
            currentPage={currentPage}
            canGoNext={canGoNext}
            canGoPrev={canGoPrev}
            onNextPage={handleNextPage}
            onPrevPage={handlePrevPage}
            totalPages={totalTakesPages}
          />
        </CollapsibleSection>
      )}

      {/* No Takes State */}
      {(!takes || takes.length === 0) && (
        <CollapsibleSection title="All Takes" icon={Activity} iconColor="text-green-500" seamless={true}>
          <div className="text-center py-8">
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
        </CollapsibleSection>
      )}
    </div>
  );
};

export default AuctionDetails;
