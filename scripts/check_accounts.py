from brownie import accounts

def main():
    print(f"Available accounts: {len(accounts)}")
    return len(accounts)