# Redis Event Testing Guide

Use `fire_events.py` to test downstream consumers (like Telegram bot) by firing events on demand.

## Quick Usage

```bash
# Single events
python3 fire_events.py deploy        # Deploy auction
python3 fire_events.py kick          # Start round  
python3 fire_events.py take          # Normal take
python3 fire_events.py take whale    # Whale take

# Realistic sequences
python3 fire_events.py sequence      # Deploy + 3 rounds of takes
python3 fire_events.py sequence 5    # Deploy + 5 rounds

# Stress testing
python3 fire_events.py stress 60 3.0 # 60s @ 3 events/second

# Interactive mode
python3 fire_events.py               # Menu-driven interface
```

## Event Types

**Deploy**: New auction deployment
**Kick**: Round start (auction kick)
**Take**: Auction take with value tiers:
- `micro`: $10-100
- `small`: $100-1K  
- `normal`: $1K-10K
- `large`: $10K-50K
- `whale`: $50K-500K
- `megawhale`: $500K-2M

## Interactive Menu Features

- Single event firing with chain selection
- Realistic event sequences (deploy → kick → takes → repeat)
- Multi-chain testing across Ethereum, Polygon, Arbitrum, etc.
- Stress testing with configurable rate/duration
- Redis stream monitoring and statistics

## Testing Downstream Consumers

Events are sent to Redis stream `events` where consumers like:
- **Telegram bot** (`scripts/consumers/telegram_consumer.py`)
- **Database indexer** 
- **API notifications**
- **Custom alerting systems**

Pick them up and process them according to their configuration.

Perfect for testing alert formatting, hyperlinking, rate limiting, and filtering logic without needing real blockchain events.