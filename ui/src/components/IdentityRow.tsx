import React, { useState } from "react";
import ChainIcon from "./ChainIcon";
import { ExternalLink, Copy, Check } from "lucide-react";
import { formatAddress, getChainInfo, copyToClipboard } from "../lib/utils";

interface IdentityRowProps {
  address: string;
  chainId: number;
}

const IdentityRow: React.FC<IdentityRowProps> = ({ address, chainId }) => {
  const [copied, setCopied] = useState(false);
  const chain = getChainInfo(chainId);

  const handleCopy = async () => {
    const ok = await copyToClipboard(address);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 800);
    }
  };

  return (
    <div className="flex items-center space-x-3">
      <ChainIcon chainId={chainId} size="xs" showName={false} />
      <div className="flex items-center space-x-2">
        <span className="font-mono text-sm text-gray-300">{address}</span>
        <button onClick={handleCopy} className="p-1 text-gray-400 hover:text-gray-200 rounded hover:bg-gray-800" title="Copy address">
          {copied ? <Check className="h-3.5 w-3.5 text-primary-500" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
        {chain.explorer !== '#' && (
          <a href={`${chain.explorer}/address/${address}`} target="_blank" rel="noopener noreferrer" className="p-1 text-gray-400 hover:text-gray-200 rounded hover:bg-gray-800" title="View on explorer">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>
    </div>
  );
};

export default IdentityRow;

