import React from "react";
import { ExternalLink } from "lucide-react";
import { formatAddress, getTxLink, getChainInfo, cn } from "../lib/utils";

interface StandardTxHashLinkProps {
  txHash: string;
  chainId: number;
  length?: number;
  className?: string;
}

/**
 * Standardized transaction hash display component
 * - Light blue text color
 * - Single external link icon
 * - No copy button (simplified)
 * - Consistent styling across all tables
 */
const StandardTxHashLink: React.FC<StandardTxHashLinkProps> = ({
  txHash,
  chainId,
  length = 5,
  className = "",
}) => {
  const chainInfo = getChainInfo(chainId);
  const hasExplorer = chainInfo?.explorer && chainInfo.explorer !== "#";
  const formattedTxHash = formatAddress(txHash, length);

  const handleExplorerClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasExplorer) {
      const url = getTxLink(txHash, chainId);
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div
      className={cn(
        "inline-flex items-center justify-center space-x-1 font-mono text-xs",
        className
      )}
      title={`${txHash} - Click to view on ${chainInfo?.name || 'blockchain'} explorer`}
    >
      {/* Transaction hash with light blue color */}
      <span className="text-primary-400 select-all">
        {formattedTxHash}
      </span>
      
      {/* Single external link icon */}
      {hasExplorer && (
        <button
          onClick={handleExplorerClick}
          className="text-primary-400 hover:text-primary-300 transition-colors duration-200 hover:scale-110"
          title={`View on ${chainInfo?.name} explorer`}
        >
          <ExternalLink className="h-3 w-3" />
        </button>
      )}
    </div>
  );
};

export default StandardTxHashLink;