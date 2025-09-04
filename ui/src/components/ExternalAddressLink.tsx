import React, { useState } from "react";
import { createPortal } from 'react-dom';
import { ExternalLink, Copy, Check } from "lucide-react";
import { formatAddress, getChainInfo, cn, copyToClipboard } from "../lib/utils";
import { useHoverTooltip } from "../hooks/useHoverTooltip";

interface ExternalAddressLinkProps {
  address: string;
  chainId: number;
  type?: "token" | "address";
  length?: number;
  className?: string;
  showFullOnHover?: boolean;
  displayText?: string; // Override display text (for tagged addresses)
}

/**
 * External address display component for non-internal addresses
 * - White text color by default
 * - Hover tooltip with copy and external link actions
 * - Space-efficient design (no inline icons)
 * - Used for addresses like TAKER that don't have internal navigation
 */
const ExternalAddressLink: React.FC<ExternalAddressLinkProps> = ({
  address,
  chainId,
  type = "address",
  length = 5,
  className = "",
  showFullOnHover = true,
  displayText,
}) => {
  const [copied, setCopied] = useState(false);
  const chainInfo = getChainInfo(chainId);
  const hasExplorer = chainInfo?.explorer && chainInfo.explorer !== "#";
  const formattedAddress = formatAddress(address, length);

  const {
    isHovered,
    tooltipPosition,
    containerRef,
    handleMouseEnter,
    handleMouseLeave,
    handleTooltipMouseEnter,
    handleTooltipMouseLeave,
  } = useHoverTooltip({ enabled: true });

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
    <>
      <div
        ref={containerRef}
        className={cn(
          "inline-flex items-center justify-center font-mono text-xs cursor-pointer",
          className
        )}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Address with white color */}
        <span className="text-white select-all">
          {displayText || formattedAddress}
        </span>
      </div>

      {/* Portal-based tooltip that renders at document level */}
      {isHovered && createPortal(
        <div 
          className="fixed pointer-events-none z-50 transition-opacity duration-200"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translateX(-50%)'
          }}
        >
          <div 
            className="flex items-center justify-center space-x-0.5 bg-gray-800 border border-gray-700 rounded-md p-1 shadow-lg pointer-events-auto"
            onMouseEnter={handleTooltipMouseEnter}
            onMouseLeave={handleTooltipMouseLeave}
          >
            {/* Copy button */}
            <button
              onClick={handleCopy}
              className="p-0.5 text-gray-500 hover:text-gray-300 transition-colors hover:scale-110"
              title="Copy address"
            >
              {copied ? (
                <Check className="h-3 w-3 text-primary-400" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </button>
            
            {/* External link button */}
            {hasExplorer && (
              <button
                onClick={handleExplorerClick}
                className="p-0.5 text-gray-500 hover:text-primary-400 transition-colors hover:scale-110"
                title={`View on ${chainInfo.name} explorer`}
              >
                <ExternalLink className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>,
        document.body
      )}
    </>
  );
};

export default ExternalAddressLink;