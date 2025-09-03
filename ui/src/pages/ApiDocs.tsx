import React, { useState } from 'react';
import { Search, Book, ExternalLink, Globe, Database, Activity, BarChart3, Clock } from 'lucide-react';
import ApiEndpoint from '../components/ApiEndpoint';
import CodeBlock from '../components/CodeBlock';

const ApiDocs: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  // API Endpoint Definitions
  const endpoints = [
    // Core Auction Endpoints
    {
      category: 'core',
      title: 'Get Auctions',
      method: 'GET' as const,
      endpoint: '/auctions',
      description: 'Retrieve a paginated list of all auctions with optional filtering by status and chain.',
      parameters: [
        { name: 'status', type: 'string' as const, enum: ['all', 'active', 'completed'], description: 'Filter auctions by their current status' },
        { name: 'page', type: 'integer' as const, description: 'Page number for pagination', example: 1 },
        { name: 'limit', type: 'integer' as const, description: 'Number of auctions per page (1-100)', example: 20 },
        { name: 'chain_id', type: 'integer' as const, description: 'Filter auctions by blockchain network', example: 1 },
      ],
      responses: [
        {
          status: 200,
          description: 'Successfully retrieved auctions',
          example: {
            auctions: [
              {
                address: '0x1234567890abcdef1234567890abcdef12345678',
                chain_id: 1,
                from_tokens: [{ symbol: 'WETH', address: '0x...', decimals: 18 }],
                want_token: { symbol: 'USDC', address: '0x...', decimals: 6 },
                current_round: {
                  round_id: 5,
                  is_active: true,
                  initial_available: '1000000000000000000',
                  time_remaining: 3600
                }
              }
            ],
            total: 50,
            page: 1,
            per_page: 20,
            has_next: true
          }
        }
      ],
      codeExamples: {
        curl: `curl -X GET "${window.location.origin}/api/auctions?status=active&limit=10" \\
  -H "Content-Type: application/json"`,
        javascript: `const response = await fetch('/api/auctions?status=active&limit=10');
const data = await response.json();
console.log(data.auctions);`,
        python: `import requests

response = requests.get('${window.location.origin}/api/auctions', 
                       params={'status': 'active', 'limit': 10})
data = response.json()
print(data['auctions'])`
      },
      tags: ['auctions', 'core']
    },
    {
      category: 'core',
      title: 'Get Auction Details',
      method: 'GET' as const,
      endpoint: '/auctions/{chain_id}/{auction_address}',
      description: 'Get comprehensive details about a specific auction including current round info and activity metrics.',
      pathParams: [
        { name: 'chain_id', type: 'integer' as const, required: true, description: 'Blockchain network ID', example: 1 },
        { name: 'auction_address', type: 'string' as const, required: true, description: 'Auction contract address', example: '0x1234567890abcdef1234567890abcdef12345678' },
      ],
      responses: [
        {
          status: 200,
          description: 'Successfully retrieved auction details',
          example: {
            address: '0x1234567890abcdef1234567890abcdef12345678',
            chain_id: 1,
            from_tokens: [{ symbol: 'WETH', address: '0x...', decimals: 18 }],
            want_token: { symbol: 'USDC', address: '0x...', decimals: 6 },
            parameters: {
              decay_rate: 0.005,
              update_interval: 36,
              auction_length: 3600,
              starting_price: '2000000000'
            },
            current_round: {
              round_id: 5,
              is_active: true,
              initial_available: '1000000000000000000',
              current_price: '1950000000',
              time_remaining: 3600
            },
            activity: {
              total_rounds: 10,
              total_takes: 45,
              total_volume: '50000000000'
            }
          }
        }
      ],
      codeExamples: {
        curl: `curl -X GET "${window.location.origin}/api/auctions/1/0x1234567890abcdef1234567890abcdef12345678" \\
  -H "Content-Type: application/json"`,
        javascript: `const response = await fetch('/api/auctions/1/0x1234567890abcdef1234567890abcdef12345678');
const auction = await response.json();
console.log(auction);`,
        python: `import requests

response = requests.get('${window.location.origin}/api/auctions/1/0x1234567890abcdef1234567890abcdef12345678')
auction = response.json()
print(auction)`
      },
      tags: ['auctions', 'details']
    },
    {
      category: 'core',
      title: 'Get Auction Takes',
      method: 'GET' as const,
      endpoint: '/auctions/{chain_id}/{auction_address}/takes',
      description: 'Retrieve all takes (purchases) for a specific auction with optional round filtering.',
      pathParams: [
        { name: 'chain_id', type: 'integer' as const, required: true, description: 'Blockchain network ID', example: 1 },
        { name: 'auction_address', type: 'string' as const, required: true, description: 'Auction contract address' },
      ],
      parameters: [
        { name: 'round_id', type: 'integer' as const, description: 'Filter takes by specific round ID' },
        { name: 'limit', type: 'integer' as const, description: 'Number of takes to return (1-100)', example: 50 },
        { name: 'offset', type: 'integer' as const, description: 'Number of takes to skip for pagination', example: 0 },
      ],
      responses: [
        {
          status: 200,
          description: 'Successfully retrieved auction takes',
          example: {
            takes: [
              {
                take_id: '0x123...abc-5-1',
                auction: '0x1234567890abcdef1234567890abcdef12345678',
                round_id: 5,
                take_seq: 1,
                taker: '0xabcdef1234567890abcdef1234567890abcdef12',
                amount_taken: '100000000000000000',
                amount_paid: '195000000',
                price: '1950000000',
                timestamp: '2024-01-15T14:30:00Z',
                tx_hash: '0xdef456...'
              }
            ],
            total: 10,
            has_more: false
          }
        }
      ],
      tags: ['auctions', 'takes', 'trading']
    },
    {
      category: 'core',
      title: 'Get Auction Rounds',
      method: 'GET' as const,
      endpoint: '/auctions/{chain_id}/{auction_address}/rounds',
      description: 'Get historical round data for a specific auction and token pair.',
      pathParams: [
        { name: 'chain_id', type: 'integer' as const, required: true, description: 'Blockchain network ID' },
        { name: 'auction_address', type: 'string' as const, required: true, description: 'Auction contract address' },
      ],
      parameters: [
        { name: 'from_token', type: 'string' as const, required: true, description: 'Token being sold address' },
        { name: 'limit', type: 'integer' as const, description: 'Number of rounds to return (1-100)', example: 50 },
      ],
      responses: [
        {
          status: 200,
          description: 'Successfully retrieved round history',
          example: {
            auction: '0x1234567890abcdef1234567890abcdef12345678',
            from_token: '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            rounds: [
              {
                round_id: 5,
                kicked_at: '2024-01-15T14:00:00Z',
                initial_available: '1000000000000000000',
                is_active: true,
                total_takes: 3
              }
            ],
            total_rounds: 10
          }
        }
      ],
      tags: ['auctions', 'rounds', 'history']
    },

    // System Endpoints
    {
      category: 'system',
      title: 'Health Check',
      method: 'GET' as const,
      endpoint: '/health',
      description: 'Check the health status of the API service and database connectivity.',
      responses: [
        {
          status: 200,
          description: 'Service is healthy',
          example: {
            status: 'healthy',
            mode: 'dev',
            mock_mode: false,
            database: 'healthy',
            timestamp: '2024-01-15T14:30:00Z'
          }
        }
      ],
      codeExamples: {
        curl: `curl -X GET "${window.location.origin}/api/health"`,
        javascript: `const response = await fetch('/api/health');
const health = await response.json();
console.log(health.status);`
      },
      tags: ['system', 'monitoring']
    },
    {
      category: 'system',
      title: 'System Statistics',
      method: 'GET' as const,
      endpoint: '/system/stats',
      description: 'Get comprehensive system statistics including total auctions, volume, and activity metrics.',
      parameters: [
        { name: 'chain_id', type: 'integer' as const, description: 'Filter statistics by specific blockchain network' },
      ],
      responses: [
        {
          status: 200,
          description: 'System statistics retrieved successfully',
          example: {
            total_auctions: 150,
            active_auctions: 12,
            unique_tokens: 45,
            total_rounds: 1250,
            total_takes: 5600,
            total_participants: 892,
            total_volume_usd: 12500000.50
          }
        }
      ],
      tags: ['system', 'analytics', 'stats']
    },
    {
      category: 'system',
      title: 'Get Tokens',
      method: 'GET' as const,
      endpoint: '/tokens',
      description: 'Retrieve information about all tokens that have been used in auctions.',
      responses: [
        {
          status: 200,
          description: 'Token information retrieved successfully',
          example: {
            tokens: [
              {
                address: '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                symbol: 'WETH',
                name: 'Wrapped Ether',
                decimals: 18,
                chain_id: 1
              },
              {
                address: '0xA0b86a33E6411C8D4E5DC8DF0D79E2B8Cb5D5Bfa',
                symbol: 'USDC',
                name: 'USD Coin',
                decimals: 6,
                chain_id: 1
              }
            ],
            count: 45
          }
        }
      ],
      tags: ['system', 'tokens', 'metadata']
    },

    // Network Endpoints
    {
      category: 'network',
      title: 'Get Chains',
      method: 'GET' as const,
      endpoint: '/chains',
      description: 'Get information about all supported blockchain networks including chain IDs, names, and block explorers.',
      responses: [
        {
          status: 200,
          description: 'Chain information retrieved successfully',
          example: {
            chains: {
              "1": {
                chainId: 1,
                name: 'Ethereum Mainnet',
                shortName: 'Ethereum',
                icon: 'https://icons.llamao.fi/icons/chains/rsz_ethereum.jpg',
                nativeSymbol: 'ETH',
                explorer: 'https://etherscan.io'
              },
              "137": {
                chainId: 137,
                name: 'Polygon',
                shortName: 'Polygon',
                icon: 'https://icons.llamao.fi/icons/chains/rsz_polygon.jpg',
                nativeSymbol: 'MATIC',
                explorer: 'https://polygonscan.com'
              }
            },
            count: 6
          }
        }
      ],
      tags: ['network', 'chains', 'metadata']
    },
    {
      category: 'network',
      title: 'Get Networks',
      method: 'GET' as const,
      endpoint: '/networks',
      description: 'Get configuration status of all enabled networks including RPC and factory configuration status.',
      responses: [
        {
          status: 200,
          description: 'Network configurations retrieved successfully',
          example: {
            networks: {
              ethereum: {
                name: 'Ethereum Mainnet',
                chain_id: 1,
                status: 'ready',
                rpc_configured: true,
                factory_configured: true,
                start_block: 18500000
              },
              local: {
                name: 'Anvil Local',
                chain_id: 31337,
                status: 'ready',
                rpc_configured: true,
                factory_configured: true,
                start_block: 0
              }
            },
            count: 2,
            mode: 'dev'
          }
        }
      ],
      tags: ['network', 'configuration', 'status']
    },

    // Analytics Endpoints
    {
      category: 'analytics',
      title: 'Recent Takes',
      method: 'GET' as const,
      endpoint: '/activity/takes',
      description: 'Get the most recent takes across all auctions, sorted by timestamp (newest first).',
      parameters: [
        { name: 'limit', type: 'integer' as const, description: 'Number of takes to return (1-500)', example: 50 },
        { name: 'chain_id', type: 'integer' as const, description: 'Filter takes by specific blockchain network' },
      ],
      responses: [
        {
          status: 200,
          description: 'Recent takes retrieved successfully',
          example: [
            {
              take_id: '0x123...abc-5-1',
              auction: '0x1234567890abcdef1234567890abcdef12345678',
              chain_id: 1,
              round_id: 5,
              taker: '0xabcdef1234567890abcdef1234567890abcdef12',
              amount_taken: '100000000000000000',
              price: '1950000000',
              timestamp: '2024-01-15T14:30:00Z',
              from_token_symbol: 'WETH',
              to_token_symbol: 'USDC'
            }
          ]
        }
      ],
      tags: ['analytics', 'activity', 'recent']
    }
  ];

  const categories = [
    { id: 'all', name: 'All Endpoints', icon: Book },
    { id: 'core', name: 'Core Auctions', icon: Database },
    { id: 'system', name: 'System', icon: Activity },
    { id: 'network', name: 'Network', icon: Globe },
    { id: 'analytics', name: 'Analytics', icon: BarChart3 },
  ];

  const filteredEndpoints = endpoints.filter(endpoint => {
    const matchesSearch = searchTerm === '' || 
      endpoint.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      endpoint.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      endpoint.endpoint.toLowerCase().includes(searchTerm.toLowerCase()) ||
      endpoint.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesCategory = selectedCategory === 'all' || endpoint.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 bg-primary-500/10 rounded-lg">
            <Book className="h-5 w-5 text-primary-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">API Documentation</h1>
            <p className="text-sm text-gray-400">Interactive documentation for the Auction System API</p>
          </div>
        </div>

        {/* API Info */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="text-center">
              <div className="text-xl font-bold text-primary-400">{endpoints.length}</div>
              <div className="text-xs text-gray-400">Endpoints</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-green-400">REST</div>
              <div className="text-xs text-gray-400">API Type</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-blue-400">JSON</div>
              <div className="text-xs text-gray-400">Response Format</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-yellow-400">v2.0</div>
              <div className="text-xs text-gray-400">API Version</div>
            </div>
          </div>
        </div>

        {/* Base URL Info */}
        <div className="bg-gray-950 border border-gray-800 rounded-lg p-3">
          <h3 className="text-xs font-medium text-gray-300 mb-2">Base URL</h3>
          <CodeBlock 
            code={`${window.location.origin}/api`} 
            language="text" 
            showCopyButton={true}
            maxHeight="max-h-12"
          />
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col lg:flex-row space-y-3 lg:space-y-0 lg:space-x-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search endpoints..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Category Filter */}
        <div className="flex space-x-1.5 overflow-x-auto">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{category.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Results Count */}
      <div className="text-xs text-gray-500">
        Showing {filteredEndpoints.length} of {endpoints.length} endpoints
      </div>

      {/* Endpoints */}
      <div className="space-y-3">
        {filteredEndpoints.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Search className="h-12 w-12 text-gray-600 mx-auto mb-3" />
            <h3 className="text-base font-medium mb-1">No endpoints found</h3>
            <p className="text-sm">Try adjusting your search terms or filters</p>
          </div>
        ) : (
          filteredEndpoints.map((endpoint, index) => (
            <ApiEndpoint
              key={index}
              title={endpoint.title}
              method={endpoint.method}
              endpoint={endpoint.endpoint}
              description={endpoint.description}
              parameters={endpoint.parameters}
              pathParams={endpoint.pathParams}
              responses={endpoint.responses}
              codeExamples={endpoint.codeExamples}
              tags={endpoint.tags}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-gray-800 text-center">
        <p className="text-gray-500 text-xs">
          Built with ❤️ for the Auction System API
        </p>
        <div className="mt-1 flex items-center justify-center space-x-3 text-xs text-gray-600">
          <span>Version 2.0.0</span>
          <span>•</span>
          <span>Interactive Documentation</span>
          <span>•</span>
          <span>Live API Testing</span>
        </div>
      </div>
    </div>
  );
};

export default ApiDocs;