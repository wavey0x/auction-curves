from brownie import Auction, accounts

def main():
    # Kick auction to generate new event for webhook testing
    auction = Auction.at('0x9f9D6AF359b4540C7b50ec0D7d6D52c8A3f5f2FA')
    tx = auction.kick({'from': accounts[0]})
    print(f'✅ Kicked auction {auction.address} at block {tx.block_number}')
    print(f'   Transaction hash: {tx.txid}')
