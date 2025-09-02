import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Check, ExternalLink } from "lucide-react";
import { formatAddress, copyToClipboard, getChainInfo, cn } from "../lib/utils";

interface AddressLinkProps {
  address: string;
  chainId: number;
  type?: "auction" | "token" | "address"; // Type determines internal linking
  length?: number;
  className?: string;
  showFullOnHover?: boolean;
}

const AddressLink: React.FC<AddressLinkProps> = ({
  address,
  chainId,
  type = "address",
  length = 5,
  className = "",
  showFullOnHover = true,
}) => {
  const [copied, setCopied] = useState(false);
  const chainInfo = getChainInfo(chainId);
  const hasExplorer = chainInfo?.explorer && chainInfo.explorer !== "#";
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

  // Determine internal link based on type
  const getInternalLink = () => {
    switch (type) {
      case "auction":
        return `/auction/${chainId}/${address}`;
      default:
        return null;
    }
  };

  const internalLink = getInternalLink();

  return (
    <div
      className={cn(
        "inline-flex flex-col items-center space-y-1 font-mono text-xs",
        className
      )}
      title={showFullOnHover ? address : undefined}
    >
      {/* Main address row with internal link (if applicable) and clipboard */}
      <div className="flex items-center space-x-1">
        {internalLink ? (
          <Link
            to={internalLink}
            className="text-primary-400 hover:text-primary-300 transition-colors select-all underline-offset-2 hover:underline"
            title={`View ${type} details`}
          >
            {formattedAddress}
          </Link>
        ) : (
          <span className="text-gray-300 select-all">
            {formattedAddress}
          </span>
        )}
        
        {/* Animated clipboard icon */}
        <button
          onClick={handleCopy}
          className="p-0.5 text-gray-500 hover:text-gray-300 transition-all duration-200 hover:scale-110"
          title="Copy address"
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
          title={`View on ${chainInfo.name} explorer`}
        >
          <ExternalLink className="h-3 w-3 group-hover:animate-pulse" />
        </button>
      )}
    </div>
  );
};

export default AddressLink;