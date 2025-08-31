#!/usr/bin/env python3
"""
Fast deployment script - no fancy UI, just speed
"""
import json
import random
import time
from brownie import accounts, AuctionFactory, LegacyAuctionFactory, Auction, LegacyAuction, MockERC20Enhanced, network

class FastDeployment:
    def __init__(self):
        self.deployer = accounts[0]
        self.receivers = accounts[1:6]
        self.tokens = {}
        self.legacy_factory = None
        self.modern_factory = None
        self.auctions = []
        
    def deploy_all(self):
        """Deploy everything quickly"""
        print("🚀 Starting FAST deployment...")
        start_time = time.time()
        
        # 1. Deploy both factories in deterministic order
        print("Deploying legacy factory (v0.0.1)...")
        self.legacy_factory = LegacyAuctionFactory.deploy({'from': self.deployer})
        print(f"✅ Legacy Factory: {self.legacy_factory.address}")
        
        print("Deploying modern factory (v0.1.0)...")
        self.modern_factory = AuctionFactory.deploy({'from': self.deployer})
        print(f"✅ Modern Factory: {self.modern_factory.address}")
        
        # 2. Tokens (batch)
        print("Deploying 10 tokens...")
        token_configs = [
            ("USDC", "USD Coin", 6, "stable"),
            ("USDT", "Tether USD", 6, "stable"),
            ("WETH", "Wrapped Ether", 18, "crypto"),
            ("WBTC", "Wrapped Bitcoin", 8, "crypto"),
            ("DAI", "Dai Stablecoin", 18, "stable"),
            ("LINK", "Chainlink", 18, "defi"),
            ("UNI", "Uniswap", 18, "defi"),
            ("AAVE", "Aave Token", 18, "defi"),
            ("CRV", "Curve DAO Token", 18, "defi"),
            ("SNX", "Synthetix", 18, "defi"),
        ]
        
        for symbol, name, decimals, category in token_configs:
            token = MockERC20Enhanced.deploy(name, symbol, decimals, {'from': self.deployer})
            self.tokens[symbol] = {
                'contract': token,
                'symbol': symbol,
                'name': name,
                'decimals': decimals,
                'category': category,
                'address': token.address
            }
        print(f"✅ Deployed {len(self.tokens)} tokens")
        
        # 3. Deploy mix of legacy and modern auctions (10 total)
        print("Deploying 10 auctions (5 legacy, 5 modern)...")
        auction_configs = [
            # Legacy auctions (first 5) - use hardcoded decay rate
            {"type": "legacy", "price_range": (500000, 2000000), "desc": "Legacy Fast"},
            {"type": "legacy", "price_range": (500000, 2000000), "desc": "Legacy Fast"}, 
            {"type": "legacy", "price_range": (100000, 1000000), "desc": "Legacy Medium"},
            {"type": "legacy", "price_range": (50000, 500000), "desc": "Legacy Slow"},
            {"type": "legacy", "price_range": (75000, 750000), "desc": "Legacy Custom"},
            # Modern auctions (last 5) - use configurable decay rate
            {"type": "modern", "decay": 995000000000000000000000000, "price_range": (100000, 1000000), "desc": "Modern Medium"},
            {"type": "modern", "decay": 998000000000000000000000000, "price_range": (50000, 500000), "desc": "Modern Slow"},
            {"type": "modern", "decay": 992000000000000000000000000, "price_range": (75000, 750000), "desc": "Modern Custom"},
            {"type": "modern", "decay": 996000000000000000000000000, "price_range": (60000, 600000), "desc": "Modern Custom"},
            {"type": "modern", "decay": 997000000000000000000000000, "price_range": (70000, 700000), "desc": "Modern Custom"},
        ]
        
        # Create simple pairs
        symbols = list(self.tokens.keys())
        pairs = [(symbols[i], symbols[(i+1) % len(symbols)]) for i in range(10)]
        
        for i, (config, (from_symbol, to_symbol)) in enumerate(zip(auction_configs, pairs)):
            to_token = self.tokens[to_symbol]
            receiver = random.choice(self.receivers)
            starting_price = random.randint(*config["price_range"])
            
            # Deploy auction based on type
            if config["type"] == "legacy":
                # Deploy legacy auction
                tx = self.legacy_factory.createNewAuction(
                    to_token['address'],
                    receiver.address,
                    self.deployer.address,
                    24 * 3600,  # 24 hours auction length 
                    starting_price,
                    {'from': self.deployer}
                )
                auction_version = "0.0.1"
                decay_rate = int(0.988514020352896135 * 1e27)  # Hardcoded legacy rate
                
            else:  # modern auction
                # Deploy modern auction
                tx = self.modern_factory.createNewAuction(
                    to_token['address'],
                    receiver.address,
                    self.deployer.address,
                    starting_price,
                    {'from': self.deployer}
                )
                auction_version = "0.1.0"
                decay_rate = config["decay"]
                
                # Set custom decay rate for modern auctions
                auction_address = tx.events['DeployedNewAuction']['auction']
                auction = Auction.at(auction_address)
                auction.setStepDecayRate(decay_rate, {'from': self.deployer})
            
            auction_address = tx.events['DeployedNewAuction']['auction']
            
            self.auctions.append({
                'address': auction_address,
                'from_token': from_symbol,
                'to_token': to_symbol,
                'description': config['desc'],
                'type': config['type'],
                'version': auction_version,
                'decay': decay_rate,
                'starting_price': starting_price,
                'receiver': receiver.address
            })
        
        print(f"✅ Deployed {len(self.auctions)} auctions")
        
        # 4. Enable & mint (FAST - no loops)
        print("Enabling tokens and minting...")
        
        enabled_count = 0
        for auction_info in self.auctions:
            # Get the appropriate auction contract
            if auction_info['type'] == 'legacy':
                auction = LegacyAuction.at(auction_info['address'])
            else:
                auction = Auction.at(auction_info['address'])
                
            from_token_contract = self.tokens[auction_info['from_token']]['contract']
            
            # Enable
            auction.enable(from_token_contract.address, {'from': self.deployer})
            
            # Mint
            decimals = self.tokens[auction_info['from_token']]['decimals'] 
            mint_amount = 1000 * (10 ** decimals)  # Fixed amount
            from_token_contract.mint(auction.address, mint_amount, {'from': self.deployer})
            
            enabled_count += 1
            
        print(f"✅ Enabled {enabled_count} token pairs")
        
        # 5. Save info and generate Rindexer config
        deployment_data = {
            'legacy_factory_address': self.legacy_factory.address,
            'modern_factory_address': self.modern_factory.address,
            'tokens': {
                symbol: {
                    'address': info['address'],
                    'name': info['name'],
                    'symbol': symbol,
                    'decimals': info['decimals'],
                    'category': info['category']
                } for symbol, info in self.tokens.items()
            },
            'auctions': self.auctions,
            'network': network.show_active(),
            'deployer': str(self.deployer),
            'block_number': network.web3.eth.block_number
        }
        
        with open('deployment_info.json', 'w') as f:
            json.dump(deployment_data, f, indent=2, default=str)
            
        # Generate Rindexer config from template
        self.generate_rindexer_config(deployment_data)
        
        total_time = time.time() - start_time
        print(f"\n🎉 DEPLOYMENT COMPLETE in {total_time:.2f} seconds!")
        print(f"📍 Legacy Factory: {self.legacy_factory.address}")
        print(f"📍 Modern Factory: {self.modern_factory.address}")
        print(f"📍 Tokens: {len(self.tokens)}")
        print(f"📍 Auctions: {len(self.auctions)}")
        print(f"📄 Saved: deployment_info.json")
        
        return self
    
    def generate_rindexer_config(self, deployment_data):
        """Generate Rindexer config from template using factory pattern with deployed addresses"""
        import os
        
        # Use the factory pattern template as source
        template_path = 'indexer/rindexer/rindexer.template.yaml'
        output_path = 'indexer/rindexer/rindexer.yaml'
        
        # Check if we're in the right directory
        if not os.path.exists(template_path):
            template_path = '../../' + template_path
            output_path = '../../' + output_path
        
        if not os.path.exists(template_path):
            print(f"⚠️ Warning: Template config not found at {template_path}")
            return
            
        try:
            with open(template_path, 'r') as f:
                config_content = f.read()
            
            # Replace template placeholders with actual deployed addresses
            config_content = config_content.replace(
                '{{MODERN_FACTORY_ADDRESS}}', 
                deployment_data['modern_factory_address']
            )
            config_content = config_content.replace(
                '{{LEGACY_FACTORY_ADDRESS}}', 
                deployment_data['legacy_factory_address']
            )
            config_content = config_content.replace(
                '{{START_BLOCK}}', 
                str(deployment_data.get('block_number', 0))
            )
            
            # Generate individual auction contract configurations
            modern_contracts = self.generate_auction_contracts(deployment_data, 'modern')
            legacy_contracts = self.generate_auction_contracts(deployment_data, 'legacy')
            
            config_content = config_content.replace(
                '{{MODERN_AUCTION_CONTRACTS}}',
                modern_contracts
            )
            config_content = config_content.replace(
                '{{LEGACY_AUCTION_CONTRACTS}}',
                legacy_contracts
            )
            
            with open(output_path, 'w') as f:
                f.write(config_content)
            
            print(f"✅ Generated Rindexer config from template: {output_path}")
            print(f"   Modern Factory: {deployment_data['modern_factory_address']}")
            print(f"   Legacy Factory: {deployment_data['legacy_factory_address']}")
            print(f"   Start Block: {deployment_data.get('block_number', 0)}")
            
        except Exception as e:
            print(f"⚠️ Error generating Rindexer config: {e}")
    
    def generate_auction_contracts(self, deployment_data, auction_type):
        """Generate individual auction contract configurations for template"""
        contracts = []
        auctions = [a for a in deployment_data.get('auctions', []) if a.get('type') == auction_type]
        
        for auction in auctions:
            contract_name = f"{auction_type.title()}Auction_{auction['from_token']}{auction['to_token']}"
            abi_file = "Auction.json" if auction_type == "modern" else "LegacyAuction.json"
            
            # Generate events list
            events = ["AuctionEnabled", "AuctionDisabled", "AuctionKicked", "UpdatedStartingPrice"]
            if auction_type == "modern":
                events.append("UpdatedStepDecayRate")
            
            # Create contract configuration
            contract_config = f'''  - name: {contract_name}
    abi: "./abis/{abi_file}"
    include_events:'''
            
            for event in events:
                contract_config += f'\n      - {event}'
                
            contract_config += f'''
    details:
      - network: local
        address: {auction['address']}
        start_block: {deployment_data.get('block_number', 0)}
    streams:
      webhooks:
        - endpoint: "http://localhost:8000/webhook/process-event"
          shared_secret: "dev_webhook_secret"
          networks:
            - local
          events:'''
            
            for event in events:
                contract_config += f'\n            - event_name: {event}'
                
            contracts.append(contract_config)
        
        return '\n\n'.join(contracts)

def main():
    """Main function"""
    deployment = FastDeployment()
    return deployment.deploy_all()

if __name__ == "__main__":
    main()