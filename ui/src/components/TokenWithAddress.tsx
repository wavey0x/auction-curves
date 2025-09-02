import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';
import { Token } from '../types/auction';
import { formatAddress, copyToClipboard, getChainInfo, cn } from '../lib/utils';

interface TokenWithAddressProps {
  token: Token;
  chainId: number;
  className?: string;
  showFullAddress?: boolean;
}

const TokenWithAddress: React.FC<TokenWithAddressProps> = ({
  token,
  chainId,
  className = '',
  showFullAddress = false,
}) => {
  const [copied, setCopied] = useState(false);
  
  const chainInfo = getChainInfo(chainId);
  const hasExplorer = chainInfo && chainInfo.explorer !== "#";

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const success = await copyToClipboard(token.address);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 600);
    }
  };

  const handleExplorerClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (hasExplorer) {
      const url = `${chainInfo.explorer}/token/${token.address}`;
      window.open(url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div
      className={cn(
        'inline-flex items-center space-x-1 text-base group',
        className
      )}
    >
      {/* Token symbol */}
      <span className="text-white font-medium">
        {token.symbol}
      </span>

      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-500 hover:text-gray-300 transition-all duration-200"
        title="Copy token address"
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
          className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-500 hover:text-primary-400 transition-all duration-200"
          title={`View ${token.symbol} on ${chainInfo.name} explorer`}
        >
          <ExternalLink className="h-3 w-3" />
        </button>
      )}

    </div>
  );
};

export default TokenWithAddress;