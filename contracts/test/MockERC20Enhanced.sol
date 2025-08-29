// SPDX-License-Identifier: MIT
pragma solidity ^0.8.18;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockERC20Enhanced
 * @notice Enhanced mock ERC20 token for testing with configurable parameters
 */
contract MockERC20Enhanced is ERC20 {
    uint8 private _decimals;
    uint256 public constant INITIAL_SUPPLY = 10_000_000; // 10M tokens
    
    /**
     * @param name_ Token name (e.g., "Wrapped Ether")
     * @param symbol_ Token symbol (e.g., "WETH")
     * @param decimals_ Number of decimals (6, 8, or 18)
     */
    constructor(
        string memory name_,
        string memory symbol_, 
        uint8 decimals_
    ) ERC20(name_, symbol_) {
        require(decimals_ <= 18, "Decimals too high");
        _decimals = decimals_;
        
        // Mint initial supply to deployer
        _mint(msg.sender, INITIAL_SUPPLY * 10**decimals_);
    }
    
    /**
     * @notice Returns the number of decimals
     */
    function decimals() public view override returns (uint8) {
        return _decimals;
    }
    
    /**
     * @notice Mint tokens to an address (testing utility)
     * @param to Address to mint tokens to
     * @param amount Amount of tokens to mint (in token units, not wei)
     */
    function mint(address to, uint256 amount) public {
        _mint(to, amount);
    }
    
    /**
     * @notice Mint tokens in wei units (for precise testing)
     * @param to Address to mint tokens to
     * @param amountWei Amount in wei (smallest unit)
     */
    function mintWei(address to, uint256 amountWei) public {
        _mint(to, amountWei);
    }
    
    /**
     * @notice Burn tokens from caller's balance
     * @param amount Amount to burn (in token units)
     */
    function burn(uint256 amount) public {
        _burn(msg.sender, amount);
    }
    
    /**
     * @notice Get token balance in human-readable format
     * @param account Account to check
     * @return Human-readable balance (with decimals)
     */
    function balanceOfFormatted(address account) public view returns (uint256) {
        return balanceOf(account) / 10**_decimals;
    }
    
    /**
     * @notice Utility function to convert human amount to wei
     * @param humanAmount Amount in human-readable format
     * @return Amount in wei
     */
    function toWei(uint256 humanAmount) public view returns (uint256) {
        return humanAmount * 10**_decimals;
    }
    
    /**
     * @notice Utility function to convert wei to human amount
     * @param weiAmount Amount in wei
     * @return Amount in human-readable format
     */
    function fromWei(uint256 weiAmount) public view returns (uint256) {
        return weiAmount / 10**_decimals;
    }
}