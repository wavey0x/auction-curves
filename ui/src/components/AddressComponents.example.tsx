/**
 * Example usage of the new Address and TxHash components
 * This file demonstrates the different use cases for the compact address components
 */

import React from "react";
import AddressLink from "./AddressLink";
import TxHashLink from "./TxHashLink";
import AddressDisplay from "./AddressDisplay"; // Legacy component
import TxHashDisplay from "./TxHashDisplay"; // Legacy component

export const AddressComponentExamples: React.FC = () => {
  // Example data
  const auctionAddress = "0x1bab8B79cB8688f1FbD1Df3f09Fa71325058448D";
  const tokenAddress = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2";
  const userAddress = "0x742d35Cc6B6B4556064A7E3D4b2d84ab6a7F1F8E";
  const txHash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";
  const chainId = 1; // Ethereum mainnet

  return (
    <div className="space-y-8 p-6">
      <h2 className="text-2xl font-bold text-gray-200">Address Component Examples</h2>
      
      <div className="space-y-6">
        {/* AddressLink Examples */}
        <section>
          <h3 className="text-xl font-semibold text-gray-300 mb-4">New AddressLink Component</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Auction Address - has internal link */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Auction Address (Internal Link)</h4>
              <AddressLink
                address={auctionAddress}
                chainId={chainId}
                type="auction"
                length={5}
              />
              <p className="text-xs text-gray-500 mt-2">
                • Abbreviated address<br/>
                • Clickable link to /auction/{chainId}/{auctionAddress}<br/>
                • Clipboard icon (animated)<br/>
                • Block explorer link below (centered)
              </p>
            </div>

            {/* Token Address */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Token Address</h4>
              <AddressLink
                address={tokenAddress}
                chainId={chainId}
                type="token"
                length={5}
              />
              <p className="text-xs text-gray-500 mt-2">
                • No internal link<br/>
                • Links to token on explorer<br/>
                • Clipboard copy<br/>
                • Block explorer link
              </p>
            </div>

            {/* Regular Address */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Regular Address</h4>
              <AddressLink
                address={userAddress}
                chainId={chainId}
                type="address"
                length={5}
              />
              <p className="text-xs text-gray-500 mt-2">
                • No internal link<br/>
                • Links to address on explorer<br/>
                • Clipboard copy<br/>
                • Block explorer link
              </p>
            </div>
          </div>
        </section>

        {/* TxHashLink Example */}
        <section>
          <h3 className="text-xl font-semibold text-gray-300 mb-4">New TxHashLink Component</h3>
          
          <div className="bg-gray-800 p-4 rounded-lg inline-block">
            <h4 className="text-sm font-medium text-gray-400 mb-2">Transaction Hash</h4>
            <TxHashLink
              txHash={txHash}
              chainId={chainId}
              length={5}
            />
            <p className="text-xs text-gray-500 mt-2">
              • Abbreviated transaction hash<br/>
              • Clipboard copy (animated)<br/>
              • Block explorer link below
            </p>
          </div>
        </section>

        {/* Legacy Components (for comparison) */}
        <section>
          <h3 className="text-xl font-semibold text-gray-300 mb-4">Legacy Components (Updated Design)</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-400 mb-2">AddressDisplay (Legacy)</h4>
              <AddressDisplay
                address={userAddress}
                chainId={chainId}
                length={5}
              />
              <p className="text-xs text-gray-500 mt-2">
                @deprecated - Use AddressLink instead
              </p>
            </div>

            <div className="bg-gray-800 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-400 mb-2">TxHashDisplay (Legacy)</h4>
              <TxHashDisplay
                txHash={txHash}
                chainId={chainId}
                length={5}
              />
              <p className="text-xs text-gray-500 mt-2">
                @deprecated - Use TxHashLink instead
              </p>
            </div>
          </div>
        </section>

        {/* Features Summary */}
        <section>
          <h3 className="text-xl font-semibold text-gray-300 mb-4">Key Features</h3>
          <div className="bg-gray-800 p-4 rounded-lg">
            <ul className="text-sm text-gray-300 space-y-2">
              <li>✅ <strong>Compact Design:</strong> Takes minimal space, perfect for tables</li>
              <li>✅ <strong>Abbreviated Display:</strong> Shows shortened addresses (configurable length)</li>
              <li>✅ <strong>Internal App Links:</strong> Auction addresses link to /auction/{chainId}/{address}</li>
              <li>✅ <strong>Animated Clipboard:</strong> Copy button with hover animations and success feedback</li>
              <li>✅ <strong>Block Explorer Links:</strong> Centered below the address, opens in new tab</li>
              <li>✅ <strong>Chain-Aware:</strong> Automatically uses correct explorer for each chain</li>
              <li>✅ <strong>Type-Safe:</strong> Full TypeScript support with proper interfaces</li>
              <li>✅ <strong>Backward Compatible:</strong> Legacy components updated with new design</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
};