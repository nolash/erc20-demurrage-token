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
	uint256 public taxLevel; // PPM
	uint256 public demurrageModifier; // PPM

	bytes32[] public redistributions; // uint40(participants) uint160(value) uint56(period) 
	mapping (address => bytes32) account;
	mapping (address => bool) minter;

	event Transfer(address indexed _from, address indexed _to, uint256 _value);
	event Approval(address indexed _owner, address indexed _spender, uint256 _value);
	event Mint(address indexed _minter, address indexed _beneficiary, uint256 _value);
	//event Debug(uint256 _foo);
	event Taxed(uint256 indexed _period);
	event Redistribution(address indexed _account, uint256 indexed _period, uint256 _value);

	constructor(string memory _name, string memory _symbol, uint32 _taxLevel, uint256 _period) {
		owner = msg.sender;
		minter[owner] = true;
		periodStart = block.number;
		periodDuration = _period;
		taxLevel = _taxLevel;
		name = _name;
		symbol = _symbol;
		decimals = 6;
		demurrageModifier = 1000000;
		bytes32 initialRedistribution = toRedistribution(0, 0, 1);
		redistributions.push(initialRedistribution);
	}

	function addMinter(address _minter) public returns (bool) {
		require(msg.sender == owner);
		minter[_minter] = true;
		return true;
	}
	
	function balanceOf(address _account) public view returns (uint256) {
		uint256 baseBalance = getBaseBalance(_account);
		uint256 inverseModifier = 1000000 - demurrageModifier;
		uint256 balanceModifier = (inverseModifier * baseBalance) / 1000000;
		return baseBalance - balanceModifier;
	}

	function getBaseBalance(address _account) private view returns (uint256) {
		return uint256(account[_account]) & 0x00ffffffffffffffffffffffffffffffffffffffff;
	}

	function increaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
		uint256 newBalance;
		
		oldBalance = getBaseBalance(_account);
		newBalance = oldBalance + _delta;
		account[_account] &= bytes32(0xffffffffffffffffffffffff0000000000000000000000000000000000000000);
		account[_account] |= bytes32(newBalance & 0x00ffffffffffffffffffffffffffffffffffffffff);
		return true;
	}

	function decreaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
	       	uint256 newBalance;

		oldBalance = getBaseBalance(_account);	
		require(oldBalance >= _delta);
		newBalance = oldBalance - _delta;
		account[_account] &= bytes32(0xffffffffffffffffffffffff0000000000000000000000000000000000000000);
		account[_account] |= bytes32(newBalance & 0x00ffffffffffffffffffffffffffffffffffffffff);
		return true;
	}

	function mintTo(address _beneficiary, uint256 _amount) external returns (bool) {
		require(minter[msg.sender]);

		// TODO: get base amount for minting
		applyTax();
		totalSupply += _amount;
		increaseBalance(_beneficiary, _amount);
		emit Mint(msg.sender, _beneficiary, _amount);
		saveRedistributionSupply();
		return true;
	}

	function toRedistribution(uint256 _participants, uint256 _value, uint256 _period) private pure returns(bytes32) {
		bytes32 redistribution;

		redistribution |= bytes32((_participants & 0xffffffffff) << 216);
		redistribution |= bytes32((_value & 0xffffffffffffffffffffffff) << 56);
		redistribution |= bytes32(_period & 0xffffffffffffff);
		return redistribution;
	}

	function toRedistributionPeriod(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & 0x00000000000000000000000000000000000000000000000000ffffffffffffff);
	}

	function toRedistributionSupply(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & 0x0000000000ffffffffffffffffffffffffffffffffffffffff00000000000000) >> 56;
	}

	function toRedistributionParticipants(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & 0xffffffffff000000000000000000000000000000000000000000000000000000) >> 216;
	}

	function redistributionCount() public view returns (uint256) {
		return redistributions.length;
	}

	function incrementRedistributionParticipants() private returns (bool) {
		uint256 currentRedistribution;
		uint256 participants;

		currentRedistribution = uint256(redistributions[redistributions.length-1]);
		participants = ((currentRedistribution & 0xffffffffff000000000000000000000000000000000000000000000000000000) >> 216) + 1;
		currentRedistribution &= 0x0000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffff;
		currentRedistribution |= participants << 216;

		//emit Debug(participants);
		redistributions[redistributions.length-1] = bytes32(currentRedistribution);
	}

	function saveRedistributionSupply() private returns (bool) {
		uint256 currentRedistribution;

		currentRedistribution = uint256(redistributions[redistributions.length-1]);
		currentRedistribution &= 0xffffffffff0000000000000000000000000000000000000000ffffffffffffff;
		currentRedistribution |= totalSupply << 56;

		redistributions[redistributions.length-1] = bytes32(currentRedistribution);
	}

	function actualPeriod() public view returns (uint256) {
		return (block.number - periodStart) / periodDuration + 1;
	}

	function checkPeriod() private view returns (bytes32) {
		bytes32 lastRedistribution;
		uint256 currentPeriod;

		lastRedistribution =  redistributions[redistributions.length-1];
		currentPeriod = this.actualPeriod();
		if (currentPeriod <= toRedistributionPeriod(lastRedistribution)) {
			return bytes32(0x00);
		}
		return lastRedistribution;
	}

	function accountPeriod(address _account) public returns (uint256) {
		return (uint256(account[_account]) & 0xffffffffffffffffffffffff0000000000000000000000000000000000000000) >> 160;
	}

	function registerAccountPeriod(address _account, uint256 _period) private returns (bool) {
		account[_account] &= 0x000000000000000000000000ffffffffffffffffffffffffffffffffffffffff;
		account[_account] |= bytes32(_period << 160);
		incrementRedistributionParticipants();
	}

	function applyTax() public returns (uint256) {
		bytes32 pendingRedistribution;
		bytes32 nextRedistribution;
		uint256 currentPeriod;

		pendingRedistribution = checkPeriod();
		if (pendingRedistribution == bytes32(0x00)) {
			return demurrageModifier;
		}
		demurrageModifier -= (demurrageModifier * taxLevel) / 1000000;
		currentPeriod = toRedistributionPeriod(pendingRedistribution);
		nextRedistribution = toRedistribution(0, totalSupply, currentPeriod + 1);
		redistributions.push(nextRedistribution);
		emit Taxed(currentPeriod);
		return demurrageModifier;
	}

	function toTaxPeriodAmount(uint256 _value, uint256 _period) public view returns (uint256) {
		uint256 valueFactor;
	      
	       	// TODO: doesn't work for solidity as floats are missing and using ints linearly increases the order of magnitude  	
		// valueFactor = 1000000 * (((1000000-taxLevel)/1000000) ** _period);
		valueFactor = 1000000;
		for (uint256 i = 0; i < _period; i++) {
			valueFactor = (valueFactor * taxLevel) / 1000000;
		}

		return (valueFactor * _value) / 1000000;
	}

	function applyRedistributionOnAccount(address _account) public returns (bool) {
		bytes32 periodRedistribution;
		uint256 supply;
		uint256 participants;
		uint256 baseValue;
		uint256 value;
		uint256 period;
	       
		period = accountPeriod(_account);
		if (period == 0 || period >= actualPeriod()) {
			return false;
		}
		periodRedistribution = redistributions[period-1];
		participants = toRedistributionParticipants(periodRedistribution);
		if (participants == 0) {
			// TODO: In this case we need to give back to everyone, so we need a total accounts counter
			revert('0 participants');
		}
		supply = toRedistributionSupply(periodRedistribution);
		// TODO: Make sure value for balance increases round down, and that we can do a single allocation to a sink account with the difference. We can use the highest bit in "participants" for that.
		baseValue = supply / participants;
		value = toTaxPeriodAmount(baseValue, period);

		account[_account] &= bytes32(0x000000000000000000000000ffffffffffffffffffffffffffffffffffffffff);
		increaseBalance(_account, value);

		emit Redistribution(_account, period, value);
		return true;
	}

	function transfer(address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;

		applyTax();
		applyRedistributionOnAccount(msg.sender);

		// TODO: Prefer to truncate the result, instead it seems to round to nearest :/
		baseValue = (_value * 1000000) / demurrageModifier;
		result = transferBase(msg.sender, _to, baseValue);

		return result;
	}

	function transferBase(address _from, address _to, uint256 _value) private returns (bool) {
		uint256 period;

		if (!decreaseBalance(_from, _value)) {
			revert('ERR_TX_DECREASEBALANCE');
		}
		if (!increaseBalance(_to, _value)) {
			revert('ERR_TX_INCREASEBALANCE');
		}
		period = actualPeriod();
		if (_value > 0 && accountPeriod(_from) != period) {
			registerAccountPeriod(_from, period);
		}
		return true;
	}
}
