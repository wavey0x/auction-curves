import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { ChevronRight, ExternalLink, Copy, Check } from 'lucide-react';
import { cn, copyToClipboard, getChainInfo } from '../lib/utils';
import { useHoverTooltip } from '../hooks/useHoverTooltip';

interface InternalLinkProps {
  to: string;
  children: React.ReactNode;
  variant?: 'default' | 'address' | 'round';
  className?: string;
  showArrow?: boolean;
  // Props for contextual actions
  address?: string;
  chainId?: number;
  showExternalLink?: boolean;
  showCopy?: boolean;
}

const InternalLink: React.FC<InternalLinkProps> = ({
  to,
  children,
  variant = 'default',
  className = '',
  showArrow = true,
  address,
  chainId,
  showExternalLink = false,
  showCopy = false,
}) => {
  const [copied, setCopied] = useState(false);
  
  const baseClasses = "internal-link group relative";
  
  const variantClasses = {
    default: "text-gray-300 hover:text-primary-300",
    address: "text-primary-400 hover:text-primary-300 font-mono",
    round: "text-gray-300 hover:text-primary-300 font-mono font-semibold",
  };

  const chainInfo = chainId ? getChainInfo(chainId) : null;
  const hasExplorer = chainInfo && chainInfo.explorer !== "#";
  
  // Determine if contextual actions should be shown based on variant
  const showContextActions = (() => {
    if (variant === 'address') {
      // Address variant automatically shows actions when address is provided
      return address && (hasExplorer || true); // Show copy always, external if explorer exists
    } else if (variant === 'round') {
      // Round variant never shows contextual actions
      return false;
    } else {
      // Default variant respects explicit props
      return (showExternalLink && hasExplorer && address) || (showCopy && address);
    }
  })();

  const {
    isHovered,
    tooltipPosition,
    containerRef,
    handleMouseEnter,
    handleMouseLeave,
    handleTooltipMouseEnter,
    handleTooltipMouseLeave,
  } = useHoverTooltip({ enabled: showContextActions });

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (address) {
      const success = await copyToClipboard(address);
      if (success) {
        setCopied(true);
        setTimeout(() => setCopied(false), 600);
      }
    }
  };

  const handleExternalLink = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasExplorer && address) {
      const url = variant === 'address' 
        ? `${chainInfo.explorer}/address/${address}`
        : `${chainInfo.explorer}/address/${address}`;
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };


  return (
    <>
      <div 
        ref={containerRef}
        className="relative inline-block internal-link-group"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Main internal link button */}
        <Link
          to={to}
          className={cn(
            baseClasses,
            variantClasses[variant],
            className
          )}
        >
          <span>{children}</span>
          {showArrow && (
            <ChevronRight className="internal-link-icon h-3 w-3" />
          )}
        </Link>
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
            {/* Copy icon first */}
            {((variant === 'address' && address) || (showCopy && address)) && (
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
            )}
            
            {/* External link icon second */}
            {((variant === 'address' && hasExplorer && address) || (showExternalLink && hasExplorer && address)) && (
              <button
                onClick={handleExternalLink}
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

export default InternalLink;