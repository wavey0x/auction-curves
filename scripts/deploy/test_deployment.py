#!/usr/bin/env python3
"""
Fast deployment script - no fancy UI, just speed
"""
import json
import random
import time
from brownie import accounts, AuctionFactory, Auction, MockERC20Enhanced, network

class FastDeployment:
    def __init__(self):
        self.deployer = accounts[0]
        self.receivers = accounts[1:6]
        self.tokens = {}
        self.factory = None
        self.auctions = []
        
    def deploy_all(self):
        """Deploy everything quickly"""
        print("🚀 Starting FAST deployment...")
        start_time = time.time()
        
        # 1. Factory
        print("Deploying factory...")
        self.factory = AuctionFactory.deploy({'from': self.deployer})
        print(f"✅ Factory: {self.factory.address}")
        
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
        
        # 3. Auctions (10 fast ones)
        print("Deploying 10 auctions...")
        auction_configs = [
            {"decay": 990000000000000000000000000, "price_range": (500000, 2000000), "desc": "Fast"},
            {"decay": 990000000000000000000000000, "price_range": (500000, 2000000), "desc": "Fast"},
            {"decay": 995000000000000000000000000, "price_range": (100000, 1000000), "desc": "Medium"},
            {"decay": 995000000000000000000000000, "price_range": (100000, 1000000), "desc": "Medium"}, 
            {"decay": 998000000000000000000000000, "price_range": (50000, 500000), "desc": "Slow"},
            {"decay": 998000000000000000000000000, "price_range": (50000, 500000), "desc": "Slow"},
            {"decay": 992000000000000000000000000, "price_range": (75000, 750000), "desc": "Custom"},
            {"decay": 991000000000000000000000000, "price_range": (80000, 800000), "desc": "Custom"},
            {"decay": 996000000000000000000000000, "price_range": (60000, 600000), "desc": "Custom"},
            {"decay": 997000000000000000000000000, "price_range": (70000, 700000), "desc": "Custom"},
        ]
        
        # Create simple pairs
        symbols = list(self.tokens.keys())
        pairs = [(symbols[i], symbols[(i+1) % len(symbols)]) for i in range(10)]
        
        for i, (config, (from_symbol, to_symbol)) in enumerate(zip(auction_configs, pairs)):
            to_token = self.tokens[to_symbol]
            receiver = random.choice(self.receivers)
            starting_price = random.randint(*config["price_range"])
            
            # Deploy auction
            tx = self.factory.createNewAuction(
                to_token['address'],
                receiver.address,
                self.deployer.address,
                starting_price,
                {'from': self.deployer}
            )
            
            auction_address = tx.events['DeployedNewAuction']['auction']
            
            # Set custom decay if needed
            if config["decay"] != 995000000000000000000000000:
                auction = Auction.at(auction_address)
                auction.setStepDecayRate(config["decay"], {'from': self.deployer})
            
            self.auctions.append({
                'address': auction_address,
                'from_token': from_symbol,
                'to_token': to_symbol,
                'description': config['desc'],
                'decay': config['decay'],
                'starting_price': starting_price,
                'receiver': receiver.address
            })
        
        print(f"✅ Deployed {len(self.auctions)} auctions")
        
        # 4. Enable & mint (FAST - no loops)
        print("Enabling tokens and minting...")
        
        enabled_count = 0
        for auction_info in self.auctions:
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
        
        # 5. Save info
        deployment_data = {
            'factory_address': self.factory.address,
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
        
        total_time = time.time() - start_time
        print(f"\n🎉 DEPLOYMENT COMPLETE in {total_time:.2f} seconds!")
        print(f"📍 Factory: {self.factory.address}")
        print(f"📍 Tokens: {len(self.tokens)}")
        print(f"📍 Auctions: {len(self.auctions)}")
        print(f"📄 Saved: deployment_info.json")
        
        return self

def main():
    """Main function"""
    deployment = FastDeployment()
    return deployment.deploy_all()

if __name__ == "__main__":
    main()