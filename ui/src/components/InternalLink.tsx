import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { ChevronRight, ExternalLink, Copy, Check } from 'lucide-react';
import { cn, copyToClipboard, getChainInfo } from '../lib/utils';

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
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const linkRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
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

  const updateTooltipPosition = () => {
    if (linkRef.current) {
      const rect = linkRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: rect.left + rect.width / 2,
        y: rect.bottom + 4
      });
    }
  };

  const handleMouseEnter = () => {
    if (showContextActions) {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
        hoverTimeoutRef.current = null;
      }
      setIsHovered(true);
      updateTooltipPosition();
    }
  };

  const handleMouseLeave = () => {
    // Add a small delay before hiding to allow cursor movement to tooltip
    hoverTimeoutRef.current = setTimeout(() => {
      setIsHovered(false);
    }, 100);
  };

  const handleTooltipMouseEnter = () => {
    // Cancel the hide timeout if cursor enters tooltip
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
  };

  const handleTooltipMouseLeave = () => {
    // Hide immediately when leaving tooltip
    setIsHovered(false);
  };

  useEffect(() => {
    if (isHovered) {
      const handleScroll = () => updateTooltipPosition();
      window.addEventListener('scroll', handleScroll, true);
      window.addEventListener('resize', handleScroll);
      return () => {
        window.removeEventListener('scroll', handleScroll, true);
        window.removeEventListener('resize', handleScroll);
      };
    }
  }, [isHovered]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  return (
    <>
      <div 
        ref={linkRef}
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
      {showContextActions && isHovered && createPortal(
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
                  <Check className="h-3 w-3 text-green-400" />
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