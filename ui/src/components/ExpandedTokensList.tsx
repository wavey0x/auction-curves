import React, { useState, useMemo } from "react";
import { Search } from "lucide-react";
import { Token } from "../types/auction";
import TokenWithAddress from "./TokenWithAddress";
import { cn } from "../lib/utils";

interface ExpandedTokensListProps {
  tokens: Token[];
  chainId: number;
  className?: string;
}

const ExpandedTokensList: React.FC<ExpandedTokensListProps> = ({
  tokens,
  chainId,
  className = "",
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  // Filter tokens based on search term
  const filteredTokens = useMemo(() => {
    if (!searchTerm.trim()) return tokens;
    
    const searchLower = searchTerm.toLowerCase();
    return tokens.filter(
      token =>
        token.symbol?.toLowerCase().includes(searchLower) ||
        token.name?.toLowerCase().includes(searchLower) ||
        token.address.toLowerCase().includes(searchLower)
    );
  }, [tokens, searchTerm]);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header with Search */}
      <div className="flex items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
          <input
            type="text"
            placeholder="Search tokens by name, symbol, or address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-xs bg-gray-800/50 border border-gray-700/50 rounded-md focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
          />
        </div>
        {searchTerm && (
          <div className="ml-3 text-xs text-gray-500">
            {filteredTokens.length} of {tokens.length}
          </div>
        )}
      </div>

      {/* Body with Scrollable Token Grid */}
      <div className="max-h-64 overflow-y-auto">
        <div className="grid grid-cols-3 gap-2">
          {filteredTokens.length > 0 ? (
            filteredTokens.map((token) => (
              <TokenWithAddress
                key={token.address}
                token={token}
                chainId={chainId}
                className="text-white font-medium"
              />
            ))
          ) : (
            <div className="col-span-3 text-center py-4 text-gray-500 text-sm">
              {searchTerm ? "No tokens match your search" : "No tokens available"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExpandedTokensList;