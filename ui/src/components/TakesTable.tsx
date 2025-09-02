import React, { useEffect, useState } from "react";
import { TrendingDown } from "lucide-react";
import type { AuctionTake, Token } from "../types/auction";
import ChainIcon from "./ChainIcon";
import AddressDisplay from "./AddressDisplay";
import TxHashDisplay from "./TxHashDisplay";
import TxHashLink from "./TxHashLink";
import AddressLink from "./AddressLink";
import InternalLink from "./InternalLink";
import {
  formatTokenAmount,
  formatReadableTokenAmount,
  formatUSD,
  formatTimeAgo,
  cn,
} from "../lib/utils";
import Pagination from "./Pagination";
import { useUserSettings } from "../context/UserSettingsContext";

interface TakesTableProps {
  takes: AuctionTake[];
  title: string;
  maxHeight?: string;
  tokens?: Token[];
  showRoundInfo?: boolean;
  auctionAddress?: string;
  hideAuctionColumn?: boolean;
  // Pagination props
  currentPage?: number;
  canGoNext?: boolean;
  canGoPrev?: boolean;
  onNextPage?: () => void;
  onPrevPage?: () => void;
}

const TakesTable: React.FC<TakesTableProps> = ({
  takes,
  title,
  maxHeight = "max-h-96",
  tokens = [],
  showRoundInfo = false,
  auctionAddress,
  hideAuctionColumn = false,
  // Pagination props
  currentPage,
  canGoNext = false,
  canGoPrev = false,
  onNextPage,
  onPrevPage,
}) => {
  const { defaultValueDisplay } = useUserSettings();
  const [showUSD, setShowUSD] = useState(defaultValueDisplay === 'usd');
  useEffect(() => {
    // Reflect updated default; user can still toggle per-table
    setShowUSD(defaultValueDisplay === 'usd');
  }, [defaultValueDisplay]);

  if (takes.length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center py-8 text-gray-500">
          <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <TrendingDown className="h-8 w-8 text-gray-600" />
          </div>
          <p className="text-lg font-medium text-gray-400">No takes yet</p>
          <p className="text-sm text-gray-600">
            Takes will appear here when auction rounds become active
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center space-x-2">
          <span>{title}</span>
          <span className="badge badge-neutral">{takes.length}</span>
        </h3>
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-800">
        <div className={cn("overflow-y-auto", maxHeight)}>
          <table className="table w-full table-fixed">
            <thead className="bg-gray-800 sticky top-0">
              <tr>
                <th className="text-center w-[22px] min-w-[22px] max-w-[22px] px-0 py-1"><span className="sr-only">Chain</span></th>
                <th className="text-center w-16 px-0.5 py-1">Take ID</th>
                <th className="text-center w-24 px-0.5 py-1">Transaction</th>
                {showRoundInfo && <th className="text-center w-16 px-0.5 py-1">Round</th>}
                {!hideAuctionColumn && <th className="text-center w-24 px-0.5 py-1">Auction</th>}
                <th 
                  className="text-center w-32 px-0.5 py-1 cursor-pointer hover:bg-gray-700/50 transition-colors"
                  onClick={() => setShowUSD(!showUSD)}
                  title="Click to toggle between token and USD values"
                >
                  Amount {showUSD ? '($)' : '(T)'}
                </th>
                <th 
                  className="text-center w-28 px-0.5 py-1 cursor-pointer hover:bg-gray-700/50 transition-colors"
                  onClick={() => setShowUSD(!showUSD)}
                  title="Click to toggle between token and USD values"
                >
                  Price {showUSD ? '($)' : '(T)'}
                </th>
                <th className="text-center w-24 px-0.5 py-1">Profit/Loss</th>
                <th className="text-center w-24 px-0.5 py-1">Taker</th>
                <th className="text-center w-20 px-0.5 py-1">Time</th>
              </tr>
            </thead>
            <tbody>
              {takes.map((take, index) => (
                <tr key={take.take_id || `take-${index}`} className="group">
                  <td className="w-[22px] min-w-[22px] max-w-[22px] px-0 py-1 text-center">
                    <div className="flex justify-center">
                      <ChainIcon
                        chainId={take.chain_id}
                        size="xs"
                        showName={false}
                      />
                    </div>
                  </td>

                  <td className="px-0.5 py-1">
                    <div className="text-sm text-center">
                      <div className="font-mono text-xs text-gray-500 leading-tight">
                        T{take.take_seq}
                      </div>
                      <div className="font-medium text-primary-400 text-xs leading-tight">
                        {take.take_id ? take.take_id.split("-").slice(-2).join("-") : 'N/A'}
                      </div>
                    </div>
                  </td>

                  <td className="px-0.5 py-1">
                    <TxHashLink
                      txHash={take.tx_hash}
                      chainId={take.chain_id}
                    />
                  </td>

                  {showRoundInfo && (
                    <td className="px-0.5 py-1">
                      <div className="flex justify-center">
                        {auctionAddress ? (
                          <InternalLink
                            to={`/round/${take.chain_id}/${auctionAddress}/${take.round_id}`}
                            variant="round"
                          >
                            R{take.round_id}
                          </InternalLink>
                        ) : (
                          <span className="font-mono text-sm text-gray-300">
                            R{take.round_id}
                          </span>
                        )}
                      </div>
                    </td>
                  )}

                  {!hideAuctionColumn && (
                    <td className="px-0.5 py-1">
                      <AddressLink
                        address={take.auction}
                        chainId={take.chain_id}
                        type="auction"
                        className="text-primary-400"
                      />
                    </td>
                  )}

                  <td className="px-0.5 py-1">
                    <div className="text-sm">
                      <div className="font-medium text-gray-200 leading-tight">
                        {showUSD ? (
                          take.amount_taken_usd ? (
                            formatUSD(parseFloat(take.amount_taken_usd))
                          ) : (
                            <span className="text-gray-500">—</span>
                          )
                        ) : (
                          `${formatReadableTokenAmount(take.amount_taken, 4)} ${take.from_token_symbol || '?'}`
                        )}
                      </div>
                      <div className="text-xs text-gray-500 leading-tight">
                        {showUSD ? (
                          take.amount_paid_usd ? (
                            formatUSD(parseFloat(take.amount_paid_usd))
                          ) : (
                            <span className="text-gray-500">—</span>
                          )
                        ) : (
                          `${formatReadableTokenAmount(take.amount_paid, 2)} ${take.to_token_symbol || '?'}`
                        )}
                      </div>
                    </div>
                  </td>

                  <td className="px-0.5 py-1">
                    <div className="text-sm">
                      <div className="font-medium text-gray-200 leading-tight">
                        {showUSD ? (
                          take.amount_taken_usd && take.amount_paid_usd ? (
                            `${formatUSD(parseFloat(take.amount_paid_usd) / parseFloat(take.amount_taken))}`
                          ) : (
                            <span className="text-gray-500">—</span>
                          )
                        ) : (
                          `${formatReadableTokenAmount(take.price, 6)} ${take.to_token_symbol || '?'}`
                        )}
                      </div>
                      <div className="text-xs text-gray-500 leading-tight">
                        / {take.from_token_symbol || '?'}
                      </div>
                    </div>
                  </td>

                  <td className="px-0.5 py-1">
                    <div className="text-sm text-center">
                      {take.price_differential_usd && take.price_differential_percent !== null ? (
                        <>
                          <div className={cn(
                            "font-medium leading-tight",
                            parseFloat(take.price_differential_usd) >= 0 
                              ? "text-green-400" 
                              : "text-red-400"
                          )}>
                            {formatUSD(Math.abs(parseFloat(take.price_differential_usd)), 2)}
                          </div>
                          <div className={cn(
                            "text-xs leading-tight font-medium",
                            parseFloat(take.price_differential_usd) >= 0 
                              ? "text-green-500" 
                              : "text-red-500"
                          )}>
                            {Math.abs(take.price_differential_percent).toFixed(2)}%
                          </div>
                        </>
                      ) : (
                        <div className="text-xs text-gray-500">
                          N/A
                        </div>
                      )}
                    </div>
                  </td>

                  <td className="px-0.5 py-1">
                    <AddressLink
                      address={take.taker}
                      chainId={take.chain_id}
                      type="address"
                      className="text-gray-400"
                    />
                  </td>

                  <td className="px-0.5 py-1">
                    <span
                      className="text-sm text-gray-400"
                      title={new Date(take.timestamp).toLocaleString()}
                    >
                      {formatTimeAgo(new Date(take.timestamp).getTime() / 1000)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unified Pagination */}
      {(onNextPage || onPrevPage) && (
        <Pagination
          currentPage={currentPage || 1}
          canGoPrev={!!canGoPrev}
          canGoNext={!!canGoNext}
          onPrev={() => onPrevPage && onPrevPage()}
          onNext={() => onNextPage && onNextPage()}
        />
      )}
    </div>
  );
};

export default TakesTable;
