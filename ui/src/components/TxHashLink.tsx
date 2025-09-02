import React, { useState } from "react";
import { Copy, Check, ExternalLink } from "lucide-react";
import { formatAddress, copyToClipboard, getTxLink, getChainInfo, cn } from "../lib/utils";

interface TxHashLinkProps {
  txHash: string;
  chainId: number;
  length?: number;
  className?: string;
  showFullOnHover?: boolean;
}

const TxHashLink: React.FC<TxHashLinkProps> = ({
  txHash,
  chainId,
  length = 5,
  className = "",
  showFullOnHover = true,
}) => {
  const [copied, setCopied] = useState(false);
  const chainInfo = getChainInfo(chainId);
  const hasExplorer = chainInfo?.explorer && chainInfo.explorer !== "#";
  const formattedTxHash = formatAddress(txHash, length);

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const success = await copyToClipboard(txHash);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 600);
    }
  };

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
        "inline-flex flex-col items-center space-y-1 font-mono text-xs",
        className
      )}
      title={showFullOnHover ? txHash : undefined}
    >
      {/* Main transaction hash row with clipboard */}
      <div className="flex items-center space-x-1">
        <span className="text-gray-400 select-all">
          {formattedTxHash}
        </span>
        
        {/* Animated clipboard icon */}
        <button
          onClick={handleCopy}
          className="p-0.5 text-gray-500 hover:text-gray-300 transition-all duration-200 hover:scale-110"
          title="Copy transaction hash"
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-400 animate-pulse" />
          ) : (
            <Copy className="h-3 w-3 hover:animate-pulse" />
          )}
        </button>
      </div>

      {/* Block explorer link centered below */}
      {hasExplorer && (
        <button
          onClick={handleExplorerClick}
          className="flex items-center justify-center p-1 text-gray-500 hover:text-primary-400 transition-all duration-200 hover:scale-110 group"
          title={`View transaction on ${chainInfo.name} explorer`}
        >
          <ExternalLink className="h-3 w-3 group-hover:animate-pulse" />
        </button>
      )}
    </div>
  );
};

export default TxHashLink;