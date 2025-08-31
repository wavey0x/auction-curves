#!/usr/bin/env python3
"""
Update indexer configuration with deployed factory addresses.
Called from deployment script to populate factory addresses in config.yaml
"""

import json
import os
import yaml
import sys
from pathlib import Path

def update_indexer_config():
    """Update indexer config with deployed contract addresses"""
    
    # File paths
    deployment_info_path = 'deployment_info.json'
    config_path = 'indexer/config.yaml'
    
    # Check if deployment info exists
    if not os.path.exists(deployment_info_path):
        print(f"❌ Deployment info not found: {deployment_info_path}")
        return False
    
    # Load deployment data
    try:
        with open(deployment_info_path, 'r') as f:
            deployment_data = json.load(f)
        print(f"✅ Loaded deployment data from {deployment_info_path}")
    except Exception as e:
        print(f"❌ Failed to load deployment data: {e}")
        return False
    
    # Load current config
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✅ Loaded indexer config from {config_path}")
    except Exception as e:
        print(f"❌ Failed to load indexer config: {e}")
        return False
    
    # Update local network factories
    if 'local' in config['networks']:
        factories = config['networks']['local']['factories']
        
        # Find and update modern factory
        for factory in factories:
            if factory['type'] == 'modern':
                old_address = factory['address']
                factory['address'] = deployment_data.get('modern_factory_address', factory['address'])
                factory['start_block'] = deployment_data.get('block_number', 0)
                print(f"✅ Updated modern factory: {old_address} -> {factory['address']}")
                break
        
        # Find and update legacy factory  
        for factory in factories:
            if factory['type'] == 'legacy':
                old_address = factory['address']
                factory['address'] = deployment_data.get('legacy_factory_address', factory['address'])
                factory['start_block'] = deployment_data.get('block_number', 0)
                print(f"✅ Updated legacy factory: {old_address} -> {factory['address']}")
                break
    
    # Write updated config
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"✅ Updated indexer configuration: {config_path}")
        
        # Show summary
        print("\n📊 Indexer Configuration Summary:")
        print(f"   Modern Factory: {deployment_data.get('modern_factory_address', 'N/A')}")
        print(f"   Legacy Factory: {deployment_data.get('legacy_factory_address', 'N/A')}")
        print(f"   Start Block: {deployment_data.get('block_number', 0)}")
        print(f"   🎯 Custom indexer will automatically track all deployed auctions")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to write updated config: {e}")
        return False

def main():
    """Main entry point"""
    if update_indexer_config():
        print("✅ Indexer configuration update completed successfully")
        sys.exit(0)
    else:
        print("❌ Indexer configuration update failed")
        sys.exit(1)

if __name__ == "__main__":
    main()