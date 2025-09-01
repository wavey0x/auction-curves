import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Copy, TrendingDown, Check } from "lucide-react";
import type { AuctionSale, Token } from "../types/auction";
import ChainIcon from "./ChainIcon";
import {
  formatAddress,
  formatTokenAmount,
  formatUSD,
  formatTimeAgo,
  getTxLink,
  getChainInfo,
  copyToClipboard,
  cn,
} from "../lib/utils";

interface TakesTableProps {
  takes: AuctionSale[];
  title: string;
  maxHeight?: string;
  tokens?: Token[];
  showRoundInfo?: boolean;
  auctionAddress?: string;
}

const TakesTable: React.FC<TakesTableProps> = ({
  takes,
  title,
  maxHeight = "max-h-96",
  tokens = [],
  showRoundInfo = false,
  auctionAddress,
}) => {
  const [copiedAddresses, setCopiedAddresses] = useState<Set<string>>(
    new Set()
  );

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

  const chainInfo = getChainInfo(31337); // Using Anvil chain

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

      <div
        className={cn(
          "overflow-hidden rounded-lg border border-gray-800",
          maxHeight
        )}
      >
        <div className="overflow-y-auto">
          <table className="table">
            <thead className="bg-gray-800/50 sticky top-0">
              <tr>
                <th className="text-center">Take ID</th>
                <th className="text-center w-16">Chain</th>
                <th className="text-center">Transaction</th>
                {showRoundInfo && <th className="text-center">Round</th>}
                <th className="text-center">Auction</th>
                <th className="text-center">Amount</th>
                <th className="text-center">Price</th>
                <th className="text-center">Taker</th>
                <th className="text-center">Time</th>
              </tr>
            </thead>
            <tbody>
              {takes.map((take, index) => (
                <tr key={take.take_id || `take-${index}`} className="group">
                  <td>
                    <div className="flex items-center space-x-1.5">
                      <TrendingDown className="h-3.5 w-3.5 text-primary-500" />
                      <div className="text-sm">
                        <div className="font-mono text-xs text-gray-500 leading-tight">
                          T{take.take_seq}
                        </div>
                        <div className="font-medium text-primary-400 text-xs leading-tight">
                          {take.take_id ? take.take_id.split("-").slice(-2).join("-") : 'N/A'}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className="w-16 text-center">
                    <div className="flex justify-center">
                      <ChainIcon
                        chainId={take.chain_id}
                        size="sm"
                        showName={false}
                      />
                    </div>
                  </td>

                  <td>
                    <div className="flex items-center space-x-2">
                      {getChainInfo(take.chain_id).explorer !== "#" ? (
                        <a
                          href={getTxLink(take.tx_hash, take.chain_id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors flex items-center space-x-1"
                          title="View transaction"
                        >
                          <span>{formatAddress(take.tx_hash)}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <button
                          onClick={() => handleCopy(take.tx_hash)}
                          className="font-mono text-sm text-gray-400 hover:text-gray-200 transition-colors flex items-center space-x-1"
                          title="Copy transaction hash"
                        >
                          <span>{formatAddress(take.tx_hash)}</span>
                          {copiedAddresses.has(take.tx_hash) ? (
                            <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </button>
                      )}
                    </div>
                  </td>

                  {showRoundInfo && (
                    <td>
                      {auctionAddress ? (
                        <Link
                          to={`/round/${take.chain_id}/${auctionAddress}/${take.round_id}`}
                          className="inline-flex items-center space-x-1 px-2 py-0.5 hover:bg-gray-800/30 rounded transition-all duration-200 group"
                        >
                          <span className="font-mono text-sm font-semibold text-gray-300 group-hover:text-primary-300">
                            R{take.round_id}
                          </span>
                        </Link>
                      ) : (
                        <div className="flex items-center space-x-1">
                          <span className="font-mono text-sm text-gray-300">
                            R{take.round_id}
                          </span>
                        </div>
                      )}
                    </td>
                  )}

                  <td>
                    <Link
                      to={`/auction/${take.chain_id}/${take.auction}`}
                      className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors"
                    >
                      {formatAddress(take.auction)}
                    </Link>
                  </td>

                  <td>
                    <div className="text-sm">
                      <div className="font-medium text-gray-200 leading-tight">
                        {formatTokenAmount(take.amount_taken, take.from_token_decimals || 18, 4)} {take.from_token_symbol || '?'}
                      </div>
                      <div className="text-xs text-gray-500 leading-tight">
                        paid: {formatTokenAmount(take.amount_paid, take.to_token_decimals || 18, 2)} {take.to_token_symbol || '?'}
                      </div>
                    </div>
                  </td>

                  <td>
                    <div className="text-sm">
                      <div className="font-medium text-gray-200 leading-tight">
                        {formatTokenAmount(take.price, take.to_token_decimals || 18, 6)} {take.to_token_symbol || '?'}
                      </div>
                      <div className="text-xs text-gray-500 leading-tight">
                        per {take.from_token_symbol || '?'}
                      </div>
                    </div>
                  </td>

                  <td>
                    <div className="flex items-center space-x-2">
                      {getChainInfo(take.chain_id).explorer !== "#" ? (
                        <a
                          href={`${
                            getChainInfo(take.chain_id).explorer
                          }/address/${take.taker}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors flex items-center space-x-1"
                          title="View address on explorer"
                        >
                          <span>{formatAddress(take.taker)}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="font-mono text-sm text-gray-400">
                          {formatAddress(take.taker)}
                        </span>
                      )}

                      <button
                        onClick={() => handleCopy(take.taker)}
                        className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
                        title="Copy address"
                      >
                        {copiedAddresses.has(take.taker) ? (
                          <Check className="h-3 w-3 text-primary-500 animate-pulse" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                  </td>

                  <td>
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
    </div>
  );
};

export default TakesTable;
