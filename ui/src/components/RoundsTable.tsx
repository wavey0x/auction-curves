import React from "react";
import ChainIcon from "./ChainIcon";
import InternalLink from "./InternalLink";
import TokenPairDisplay from "./TokenPairDisplay";
import Pagination from "./Pagination";
import { cn, formatTimeAgo, formatTokenAmount } from "../lib/utils";

interface RoundItem {
  round_id: number;
  kicked_at: string; // ISO string
  round_start?: number;
  round_end?: number;
  initial_available: string; // raw units
  is_active: boolean;
  total_takes: number;
  from_token: string; // address
}

interface TokenMeta {
  address: string;
  symbol?: string;
  name?: string;
  decimals?: number;
}

interface RoundsTableProps {
  rounds: RoundItem[];
  auctionAddress: string;
  chainId: number;
  fromTokens: TokenMeta[];
  wantToken?: TokenMeta;
  title?: string;
  currentPage?: number;
  perPage?: number;
  // Pagination props
  canGoNext?: boolean;
  canGoPrev?: boolean;
  onNextPage?: () => void;
  onPrevPage?: () => void;
  totalPages?: number;
}

const RoundsTable: React.FC<RoundsTableProps> = ({
  rounds,
  auctionAddress,
  chainId,
  fromTokens,
  wantToken,
  title = "Rounds",
  currentPage,
  canGoNext = false,
  canGoPrev = false,
  onNextPage,
  onPrevPage,
  totalPages,
}) => {
  const tokenMap: Record<string, TokenMeta> = Object.fromEntries(
    fromTokens.map(t => [t.address.toLowerCase(), t])
  );

  return (
    <>
      {title && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center space-x-2">
            <span>{title}</span>
            <span className="badge badge-neutral">{rounds.length}</span>
          </h3>
        </div>
      )}

      <div className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="table w-full">
            <thead className="bg-gray-800/50">
              <tr>
                <th className="text-center w-[32px] min-w-[32px] max-w-[32px] pl-4 pr-2 py-2"><span className="sr-only">Chain</span></th>
                <th className="text-center py-2">Round</th>
                <th className="text-center py-2">Tokens</th>
                <th className="text-center py-2">Kicked</th>
                <th className="text-center py-2">Status</th>
                <th className="text-center py-2">Starting Amount</th>
                <th className="text-center py-2">Takes</th>
              </tr>
            </thead>
            <tbody>
              {rounds.map((r, idx) => {
                const fromMeta = tokenMap[r.from_token.toLowerCase()];
                const fromSymbol = fromMeta?.symbol || r.from_token.slice(0,6) + "…" + r.from_token.slice(-4);
                const wantSymbol = wantToken?.symbol || "WANT";
                const decimals = fromMeta?.decimals ?? 18;
                const kickedAt = new Date(r.kicked_at);
                const isActive = r.is_active;
                return (
                  <tr key={`${r.round_id}-${r.from_token}-${idx}`} className="group">
                    <td className="w-[32px] min-w-[32px] max-w-[32px] pl-4 pr-2 text-center">
                      <div className="flex justify-center">
                        <ChainIcon chainId={chainId} size="xs" showName={false} />
                      </div>
                    </td>
                    <td className="text-center">
                      <InternalLink
                        to={`/round/${chainId}/${auctionAddress}/${r.round_id}`}
                        variant="round"
                      >
                        R{r.round_id}
                      </InternalLink>
                    </td>
                    <td className="text-center">
                      <TokenPairDisplay
                        fromToken={fromSymbol}
                        toToken={wantSymbol}
                      />
                    </td>
                    <td className="text-center">
                      <span className="text-sm text-gray-400" title={kickedAt.toLocaleString()}>
                        {formatTimeAgo(Math.floor(kickedAt.getTime()/1000))}
                      </span>
                    </td>
                    <td className="text-center">
                      <div className="flex justify-center">
                        <div className="flex items-center space-x-2">
                          <div className={`h-2 w-2 rounded-full ${isActive ? 'bg-success-500 animate-pulse' : 'bg-gray-600'}`}></div>
                          <span className={`text-sm font-medium ${isActive ? 'text-success-400' : 'text-gray-500'}`}>
                            {isActive ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="text-center">
                      <span className="font-mono text-sm text-gray-200">
                        {formatTokenAmount(r.initial_available || "0", decimals, 2)}
                      </span>
                    </td>
                    <td className="text-center">
                      <span className="text-sm text-gray-300">{r.total_takes}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {(onNextPage || onPrevPage) && (
        <Pagination
          currentPage={currentPage || 1}
          canGoPrev={!!canGoPrev}
          canGoNext={!!canGoNext}
          onPrev={() => onPrevPage && onPrevPage()}
          onNext={() => onNextPage && onNextPage()}
          totalPages={totalPages}
        />
      )}
    </>
  );
};

export default RoundsTable;

