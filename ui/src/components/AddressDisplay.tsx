import React, { useState } from "react";
import { Copy, Check, ExternalLink } from "lucide-react";
import { formatAddress, copyToClipboard, getChainInfo, cn } from "../lib/utils";

interface AddressDisplayProps {
  address: string;
  chainId?: number;
  length?: number;
  className?: string;
  showFullOnHover?: boolean;
  type?: "address" | "token"; // Type determines explorer link format
}

/**
 * @deprecated Use AddressLink for new implementations.
 * This component is kept for backward compatibility.
 */
const AddressDisplay: React.FC<AddressDisplayProps> = ({
  address,
  chainId,
  length = 5,
  className = "",
  showFullOnHover = true,
  type = "address",
}) => {
  const [copied, setCopied] = useState(false);
  const chainInfo = chainId ? getChainInfo(chainId) : null;
  const hasExplorer = chainInfo && chainInfo.explorer !== "#";
  const formattedAddress = formatAddress(address, length);

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const success = await copyToClipboard(address);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 600);
    }
  };

  const handleExplorerClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasExplorer) {
      const url = type === "token" 
        ? `${chainInfo.explorer}/token/${address}`
        : `${chainInfo.explorer}/address/${address}`;
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div
      className={cn(
        "inline-flex flex-col items-center space-y-1 font-mono text-xs",
        className
      )}
      title={showFullOnHover ? address : undefined}
    >
      {/* Main address row with clipboard */}
      <div className="flex items-center space-x-1">
        <span className="text-gray-300 select-all">
          {formattedAddress}
        </span>
        
        {/* Animated clipboard icon */}
        <button
          onClick={handleCopy}
          className="p-0.5 text-gray-500 hover:text-gray-300 transition-all duration-200 hover:scale-110"
          title="Copy address"
        >
          {copied ? (
            <Check className="h-3 w-3 text-primary-400 animate-pulse" />
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
          title={`View on ${chainInfo.name} explorer`}
        >
          <ExternalLink className="h-3 w-3 group-hover:animate-pulse" />
        </button>
      )}
    </div>
  );
};

export default AddressDisplay;