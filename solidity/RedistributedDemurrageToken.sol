pragma solidity > 0.6.11;

// SPDX-License-Identifier: GPL-3.0-or-later

contract RedistributedDemurrageToken {

	address public owner;
	uint256 public decimals;
	string public name;
	string public symbol;
	uint256 public totalSupply;

	uint256 public periodStart;
	uint256 public periodDuration;
	uint32 public taxLevel;
	uint256 public demurrageModifier;

	bytes32[] redistributions; // uint40(participants) uint160(value) uint56(period) 

	event Transfer(address indexed _from, address indexed _to, uint256 _value);
	event Approval(address indexed _owner, address indexed _spender, uint256 _value);

	constructor(string memory _name, string memory _symbol, uint32 _taxLevel, uint256 _period) {
		owner = msg.sender;
		periodStart = block.number;
		periodDuration = _period;
		taxLevel = _taxLevel;
		name = _name;
		symbol = _symbol;
		decimals = 6;
		bytes32 initialRedistribution = toRedistribution(0, 1, 0);
		redistributions.push(initialRedistribution);
	}

	function toRedistribution(uint256 _participants, uint256 _value, uint256 _period) private pure returns(bytes32) {
		bytes32 redistribution;
		redistribution |= bytes32((_participants & 0xffffffffff) << 215);
		redistribution |= bytes32((_value & 0xffffffffffffffffffffffff) << 55);
		redistribution |= bytes32((_period & 0xffffffffffffff) << 55);
		return redistribution;
	}

	function toRedistributionPeriod(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & bytes7(0xffffffffffffff));
	}

	function redistributionCount() public view returns (uint256) {
		return redistributions.length;
	}

	function actualPeriod() public view returns (uint256) {
		return (block.number - periodStart) / periodDuration;
	}

	function checkPeriod() private view returns (bytes32) {
		bytes32 lastRedistribution = redistributions[redistributions.length-1];
		uint256 currentPeriod = this.actualPeriod();
		if (currentPeriod < toRedistributionPeriod(lastRedistribution)) {
			return bytes32(0x00);
		}
		return lastRedistribution;
	}

	function applyTax() public returns (uint256) {
		bytes32 pendingRedistribution;
		bytes32 nextRedistribution;

		pendingRedistribution = checkPeriod();
		if (pendingRedistribution == bytes32(0x00)) {
			return demurrageModifier;	
		}
		demurrageModifier += taxLevel;
		nextRedistribution = toRedistribution(0, actualPeriod(), 0);
		redistributions.push(nextRedistribution);
		return demurrageModifier;
	}

	function noop() public returns (uint256) {
		return 0;
	}
}
