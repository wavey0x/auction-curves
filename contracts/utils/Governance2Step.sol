// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.8.18;

contract Governance2Step {
    address public governance;
    address public pendingGovernance;

    event GovernanceTransferred(address indexed previousGovernance, address indexed newGovernance);

    modifier onlyGovernance() {
        require(msg.sender == governance, "!governance");
        _;
    }

    constructor(address _governance) {
        governance = _governance;
        emit GovernanceTransferred(address(0), _governance);
    }

    function transferGovernance(address _pendingGovernance) external onlyGovernance {
        pendingGovernance = _pendingGovernance;
    }

    function acceptGovernance() external {
        require(msg.sender == pendingGovernance, "!pending");
        emit GovernanceTransferred(governance, pendingGovernance);
        governance = pendingGovernance;
        pendingGovernance = address(0);
    }
}