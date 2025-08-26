// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.8.18;

interface ITaker {
    function auctionTakeCallback(
        address _from,
        address _sender,
        uint256 _amountTaken,
        uint256 _needed,
        bytes calldata _data
    ) external;
}