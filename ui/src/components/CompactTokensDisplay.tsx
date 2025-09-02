import React from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Token } from "../types/auction";
import TokenWithAddress from "./TokenWithAddress";

interface CompactTokensDisplayProps {
  tokens: Token[];
  maxDisplay?: number;
  isExpanded?: boolean;
  onToggle?: () => void;
  className?: string;
  chainId?: number;
}

const CompactTokensDisplay: React.FC<CompactTokensDisplayProps> = ({
  tokens,
  maxDisplay = 2,
  isExpanded = false,
  onToggle,
  className = "",
  chainId,
}) => {
  if (!tokens || tokens.length === 0) {
    return <span className="text-gray-500 text-sm">—</span>;
  }

  const visibleTokens = tokens.slice(0, maxDisplay);
  const hiddenCount = tokens.length - maxDisplay;
  const hasMore = hiddenCount > 0;

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* Show tokens only when collapsed */}
      {!isExpanded && (
        <div className="flex flex-wrap items-center gap-1">
          {visibleTokens.map((token, index) => (
            <React.Fragment key={token.address}>
              {chainId ? (
                <TokenWithAddress
                  token={token}
                  chainId={chainId}
                  className="text-white font-medium hover:text-primary-300"
                  showSymbolOnly={true}
                />
              ) : (
                <span className="text-white font-medium">
                  {token.symbol}
                </span>
              )}
              {index < visibleTokens.length - 1 && (
                <span className="text-gray-500">,</span>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Show total count when expanded */}
      {isExpanded && (
        <span className="text-sm text-gray-400">
          {tokens.length} {tokens.length === 1 ? 'token' : 'tokens'} enabled
        </span>
      )}

      {/* Toggle button */}
      {hasMore && onToggle && (
        <button
          onClick={onToggle}
          className="inline-flex items-center space-x-1 px-2 py-1 rounded-md bg-gray-700/30 hover:bg-gray-700/50 transition-colors text-xs text-gray-400 hover:text-gray-300"
        >
          {isExpanded ? (
            <>
              <span>Show less</span>
              <ChevronUp className="h-3 w-3" />
            </>
          ) : (
            <>
              <span>+{hiddenCount} more</span>
              <ChevronDown className="h-3 w-3" />
            </>
          )}
        </button>
      )}

      {!hasMore && !isExpanded && tokens.length <= maxDisplay && (
        <span className="text-xs text-gray-500">
          ({tokens.length} {tokens.length === 1 ? 'token' : 'tokens'})
        </span>
      )}
    </div>
  );
};

export default CompactTokensDisplay;