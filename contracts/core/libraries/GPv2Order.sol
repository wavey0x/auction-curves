// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.8.18;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

library GPv2Order {
    struct Data {
        IERC20 sellToken;
        IERC20 buyToken;
        address receiver;
        uint256 sellAmount;
        uint256 buyAmount;
        uint32 validTo;
        bytes32 appData;
        uint256 feeAmount;
        bytes32 kind;
        bool partiallyFillable;
        bytes32 sellTokenBalance;
        bytes32 buyTokenBalance;
    }

    function hash(Data memory order, bytes32 domainSeparator) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(domainSeparator, order.sellToken, order.buyToken));
    }
}