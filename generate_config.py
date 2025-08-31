#!/usr/bin/env python3
"""
Factory pattern config generator for Rindexer using correct structure.
Pure factory discovery approach with unified tables per event type.
"""
import json
import os

def main():
    """Generate Rindexer config from template using proper factory pattern"""
    template_path = 'indexer/rindexer/rindexer.template.yaml'
    output_path = 'indexer/rindexer/rindexer.yaml'
    
    # Load deployment data
    with open('deployment_info.json', 'r') as f:
        deployment_data = json.load(f)
    
    # Load template
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
    
    # Write output
    with open(output_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Generated Rindexer config using factory pattern: {output_path}")
    print(f"   Modern Factory: {deployment_data['modern_factory_address']}")
    print(f"   Legacy Factory: {deployment_data['legacy_factory_address']}")
    print(f"   Start Block: {deployment_data.get('block_number', 0)}")
    print(f"   🎯 Factory discovery will automatically index ALL deployed auctions")
    print(f"   📊 Unified tables: auction_kicked, legacy_auction_kicked, etc.")
    print(f"   ✨ Using corrected factory structure from user guidance")

if __name__ == "__main__":
    main()