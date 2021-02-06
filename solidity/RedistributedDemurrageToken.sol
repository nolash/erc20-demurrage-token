pragma solidity > 0.6.11;

// SPDX-License-Identifier: GPL-3.0-or-later

// TODO: assign bitmask values to contants 
contract RedistributedDemurrageToken {

	address public owner;
	string public name;
	string public symbol;
	uint256 public decimals;
	uint256 public totalSupply;
	uint256 public minimumParticipantSpend;
	uint256 constant ppmDivider = 100000000000000000000000000000000;

	uint256 public immutable periodStart; // timestamp
	uint256 public immutable periodDuration; // duration in SECONDS
	uint256 public immutable taxLevel; // PPM per MINUTE
	uint256 public demurrageModifier; // PPM uint128(block) | uint128(ppm)

	//bytes32[] public redistributions; // uint1(isFractional) | uint1(unused) | uint38(participants) | uint160(value) | uint56(period)
	bytes32[] public redistributions; // uint1(isFractional) | uint95(unused) | uint20(demurrageModifier) | uint36(participants) | uint72(value) | uint32(period)
	//mapping (address => bytes32) account; // uint20(unused) | uint56(period) | uint160(value)
	mapping (address => bytes32) account; // uint152(unused) | uint32(period) | uint72(value)
	mapping (address => bool) minter;
	mapping (address => mapping (address => uint256 ) ) allowance; // holder -> spender -> amount (amount is subject to demurrage)

	address sinkAddress; // receives redistribuion remainders

	event Transfer(address indexed _from, address indexed _to, uint256 _value);
	event Approval(address indexed _owner, address indexed _spender, uint256 _value);
	event Mint(address indexed _minter, address indexed _beneficiary, uint256 _value);
	//event Debug(uint256 _foo);
	event Decayed(uint256 indexed _period, uint256 indexed _periodCount, uint256 indexed _oldAmount, uint256 _newAmount);
	event Redistribution(address indexed _account, uint256 indexed _period, uint256 _value);

	constructor(string memory _name, string memory _symbol, uint8 _decimals, uint256 _taxLevelMinute, uint256 _periodMinutes, address _defaultSinkAddress) public {
		owner = msg.sender;
		minter[owner] = true;
		periodStart = block.timestamp;
		periodDuration = _periodMinutes * 60;
		name = _name;
		symbol = _symbol;
		decimals = _decimals;
		demurrageModifier = ppmDivider * 1000000; // Emulates 38 decimal places
		demurrageModifier |= (1 << 128);
		taxLevel = _taxLevelMinute; // 38 decimal places
		sinkAddress = _defaultSinkAddress;
		bytes32 initialRedistribution = toRedistribution(0, 1000000, 0, 1);
		redistributions.push(initialRedistribution);
		minimumParticipantSpend = 10 ** uint256(_decimals);
	}

	// Given address will be allowed to call the mintTo() function
	function addMinter(address _minter) public returns (bool) {
		require(msg.sender == owner);
		minter[_minter] = true;
		return true;
	}

	/// ERC20
	function balanceOf(address _account) public view returns (uint256) {
		uint256 baseBalance;
		uint256 anchorDemurrageAmount;
		uint256 anchorDemurragePeriod;
		uint256 currentDemurrageAmount;
		uint256 periodCount;

		baseBalance = getBaseBalance(_account);
		anchorDemurrageAmount = toDemurrageAmount(demurrageModifier);
		anchorDemurragePeriod = toDemurragePeriod(demurrageModifier);

		periodCount = actualPeriod() - toDemurragePeriod(demurrageModifier);

		currentDemurrageAmount = toTaxPeriodAmount(anchorDemurrageAmount, periodCount);

		return (baseBalance * currentDemurrageAmount) / (ppmDivider * 1000000);
	}

	/// Balance unmodified by demurrage
	function getBaseBalance(address _account) private view returns (uint256) {
		//return uint256(account[_account]) & 0x00ffffffffffffffffffffffffffffffffffffffff;
		return uint256(account[_account]) & 0xffffffffffffffffff;
	}

	/// Increases base balance for a single account
	function increaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
		uint256 newBalance;
		uint256 workAccount;

		workAccount = uint256(account[_account]); // | (newBalance & 0xffffffffffffffffff);
	
		if (_delta == 0) {
			return false;
		}

		oldBalance = getBaseBalance(_account);
		newBalance = oldBalance + _delta;
		require(uint160(newBalance) > uint160(oldBalance), 'ERR_WOULDWRAP'); // revert if increase would result in a wrapped value
		//account[_account] &= bytes32(0xfffffffffffffffffffffff0000000000000000000000000000000000000000);
		//account[_account] = bytes32(uint256(account[_account]) & 0xfffffffffffffffffffffffffffffffffffffffffffff000000000000000000);
		workAccount &= 0xfffffffffffffffffffffffffffffffffffffffffffff000000000000000000;
		//account[_account] |= bytes32(newBalance & 0x00ffffffffffffffffffffffffffffffffffffffff);
		workAccount |= newBalance & 0xffffffffffffffffff;
		account[_account] = bytes32(workAccount);
		return true;
	}

	/// Decreases base balance for a single account
	function decreaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
	       	uint256 newBalance;
		uint256 workAccount;

		workAccount = uint256(account[_account]); // | (newBalance & 0xffffffffffffffffff);

		if (_delta == 0) {
			return false;
		}

		oldBalance = getBaseBalance(_account);	
		require(oldBalance >= _delta, 'ERR_OVERSPEND'); // overspend guard
		newBalance = oldBalance - _delta;
		//account[_account] &= bytes32(0xffffffffffffffffffffffff0000000000000000000000000000000000000000);
		workAccount &= 0xfffffffffffffffffffffffffffffffffffffffffffff000000000000000000;
		//account[_account] |= bytes32(newBalance & 0x00ffffffffffffffffffffffffffffffffffffffff);
		workAccount |= newBalance & 0xffffffffffffffffff;
		account[_account] = bytes32(workAccount);
		return true;
	}

	// Creates new tokens out of thin air, and allocates them to the given address
	// Triggers tax
	function mintTo(address _beneficiary, uint256 _amount) external returns (bool) {
		uint256 baseAmount;

		require(minter[msg.sender]);

		applyDemurrage();
		changePeriod();
		baseAmount = _amount;
		totalSupply += _amount;
		increaseBaseBalance(_beneficiary, baseAmount);
		emit Mint(msg.sender, _beneficiary, _amount);
		saveRedistributionSupply();
		return true;
	}

	// Deserializes the redistribution word
	// uint1(isFractional) | uint95(unused) | uint20(demurrageModifier) | uint36(participants) | uint72(value) | uint32(period)
	function toRedistribution(uint256 _participants, uint256 _demurrageModifierPpm, uint256 _value, uint256 _period) private pure returns(bytes32) {
		bytes32 redistribution;

		redistribution |= bytes32((_demurrageModifierPpm & 0x0fffff) << 140);
		redistribution |= bytes32((_participants & 0x0fffffffff) << 104);
		redistribution |= bytes32((_value & 0xffffffffffffffffff) << 32);
		redistribution |= bytes32(_period & 0xffffffff);
		return redistribution;
	}

	// Serializes the demurrage period part of the redistribution word
	function toRedistributionPeriod(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution) & 0xffffffff;
	}

	// Serializes the supply part of the redistribution word
	function toRedistributionSupply(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & 0x00000000000000000000000000000000000000ffffffffffffffffff00000000) >> 32;
	}

	// Serializes the number of participants part of the redistribution word
	function toRedistributionParticipants(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & 0x00000000000000000000000000000fffffffff00000000000000000000000000) >> 104;
	}

	// Serializes the number of participants part of the redistribution word
	function toRedistributionDemurrageModifier(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution & 0x000000000000000000000000fffff00000000000000000000000000000000000) >> 140;
	}

	// Client accessor to the redistributions array length
	function redistributionCount() public view returns (uint256) {
		return redistributions.length;
	}

	// Add number of participants for the current redistribution period by one
	function incrementRedistributionParticipants() private returns (bool) {
		bytes32 currentRedistribution;
		uint256 tmpRedistribution;
		uint256 participants;

		currentRedistribution = redistributions[redistributions.length-1];
		participants = toRedistributionParticipants(currentRedistribution) + 1;
		tmpRedistribution = uint256(currentRedistribution);
		tmpRedistribution &= 0xfffffffffffffffffffffffffffff000000000ffffffffffffffffffffffffff;
		tmpRedistribution |= (participants & 0x0fffffffff) << 104;

		redistributions[redistributions.length-1] = bytes32(tmpRedistribution);
	}

	// Save the current total supply amount to the current redistribution period
	function saveRedistributionSupply() private returns (bool) {
		uint256 currentRedistribution;

		currentRedistribution = uint256(redistributions[redistributions.length-1]);
		currentRedistribution &= 0xffffffffffffffffffffffffffffffffffffff000000000000000000ffffffff;
		currentRedistribution |= totalSupply << 32;

		redistributions[redistributions.length-1] = bytes32(currentRedistribution);
	}

	// Get the demurrage period of the current block number
	function actualPeriod() public view returns (uint256) {
		return (block.timestamp - periodStart) / periodDuration + 1;
	}

	// Add an entered demurrage period to the redistribution array
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

	// Deserialize the pemurrage period for the given account is participating in
	function accountPeriod(address _account) public view returns (uint256) {
		//return (uint256(account[_account]) & 0xffffffffffffffffffffffff0000000000000000000000000000000000000000) >> 160;
		return (uint256(account[_account]) & 0x00000000000000000000000000000000000000ffffffff000000000000000000) >> 72;
	}

	// Save the given demurrage period as the currently participation period for the given address
	function registerAccountPeriod(address _account, uint256 _period) private returns (bool) {
		//account[_account] &= 0x000000000000000000000000ffffffffffffffffffffffffffffffffffffffff;
		account[_account] &= 0xffffffffffffffffffffffffffffffffffffff00000000ffffffffffffffffff;
		account[_account] |= bytes32(_period << 72);
		incrementRedistributionParticipants();
	}

	// Determine whether the unit number is rounded down, rounded up or evenly divides.
	// Returns 0 if evenly distributed, or the remainder as a positive number
	// A _numParts value 0 will be interpreted as the value 1
	function remainder(uint256 _numParts, uint256 _sumWhole) public pure returns (uint256) {
		uint256 unit;
		uint256 truncatedResult;

		if (_numParts == 0) { // no division by zero please
			revert('ERR_NUMPARTS_ZERO');
		}
		require(_numParts < _sumWhole); // At least you are never LESS than the sum of your parts. Think about that.

		unit = _sumWhole / _numParts;
		truncatedResult = unit * _numParts;
		return _sumWhole - truncatedResult;
	}

	// Called in the edge case where participant number is 0. It will override the participant count to 1.
	// Returns the remainder sent to the sink address
	function applyDefaultRedistribution(bytes32 _redistribution) private returns (uint256) {
		uint256 redistributionSupply;
		uint256 redistributionPeriod;
		uint256 unit;
		uint256 truncatedResult;

		redistributionSupply = toRedistributionSupply(_redistribution);

		unit = (redistributionSupply * taxLevel) / 1000000;
		truncatedResult = (unit * 1000000) / taxLevel;

		if (truncatedResult < redistributionSupply) {
			redistributionPeriod = toRedistributionPeriod(_redistribution); // since we reuse period here, can possibly be optimized by passing period instead
			//redistributions[redistributionPeriod-1] &= 0x0000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffff; // just to be safe, zero out all participant count data, in this case there will be only one
			redistributions[redistributionPeriod-1] &= 0xfffffffffffffffffffffffffffff000000000ffffffffffffffffffffffffff; // just to be safe, zero out all participant count data, in this case there will be only one
			//redistributions[redistributionPeriod-1] |= 0x8000000001000000000000000000000000000000000000000000000000000000;
			redistributions[redistributionPeriod-1] |= 0x8000000000000000000000000000000000000100000000000000000000000000;
		}

		increaseBaseBalance(sinkAddress, unit / ppmDivider); //truncatedResult);
		return unit;
	}

	// sets the remainder bit for the given period and books the remainder to the sink address balance
	// returns false if no change was made
	function applyRemainderOnPeriod(uint256 _remainder, uint256 _period) private returns (bool) {
		uint256 periodSupply;

		if (_remainder == 0) {
			return false;
		}

		// is this needed?
		redistributions[_period-1] |= 0x8000000000000000000000000000000000000000000000000000000000000000;

		periodSupply = toRedistributionSupply(redistributions[_period-1]);
		increaseBaseBalance(sinkAddress, periodSupply - _remainder);
		return true;
	}


	function toDemurrageAmount(uint256 _demurrage) public pure returns (uint256) {
		return _demurrage & 0x00000000000000000000000000000000ffffffffffffffffffffffffffffffff;
	}

	function toDemurragePeriod(uint256 _demurrage) public pure returns (uint256) {
		return (_demurrage & 0xffffffffffffffffffffffffffffffff00000000000000000000000000000000) >> 128;
	}

	function applyDemurrage() public returns (bool) {
		uint256 epochPeriodCount;
		uint256 periodCount;
		uint256 lastDemurrageAmount;
		uint256 newDemurrageAmount;

		epochPeriodCount = actualPeriod();
		//epochPeriodCount = (block.timestamp - periodStart) / periodDuration; // toDemurrageTime(demurrageModifier);
		periodCount = epochPeriodCount - toDemurragePeriod(demurrageModifier);
		if (periodCount == 0) {
			return false;
		}
		lastDemurrageAmount = toDemurrageAmount(demurrageModifier);
		newDemurrageAmount = toTaxPeriodAmount(lastDemurrageAmount, periodCount);
		demurrageModifier = 0;
		demurrageModifier |= (newDemurrageAmount & 0x00000000000000000000000000000000ffffffffffffffffffffffffffffffff);
		demurrageModifier |= (epochPeriodCount << 128);
		emit Decayed(epochPeriodCount, periodCount, lastDemurrageAmount, newDemurrageAmount);
		return true;
	}

	// Return timestamp of start of period threshold
	function getPeriodTimeDelta(uint256 _periodCount) public view returns (uint256) {
		return periodStart + (_periodCount * periodDuration);
	}

	// Amount of demurrage cycles inbetween the current timestamp and the given target time
	function demurrageCycles(uint256 _target) public view returns (uint256) {
		return (block.timestamp - _target) / 60;
	}

	// Recalculate the demurrage modifier for the new period
	// After this, all REPORTED balances will have been reduced by the corresponding ratio (but the effecive totalsupply stays the same)
	//function applyTax() public returns (uint256) {
	function changePeriod() public returns (bool) {
		bytes32 currentRedistribution;
		bytes32 nextRedistribution;
		uint256 currentPeriod;
		uint256 currentParticipants;
		uint256 currentRemainder;
		uint256 currentRedistributionDemurrage;
		uint256 demurrageCounts;
		uint256 periodTimestamp;

		currentRedistribution = checkPeriod();
		if (currentRedistribution == bytes32(0x00)) {
			return false;
		}
		periodTimestamp = getPeriodTimeDelta(currentPeriod);
		demurrageCounts = demurrageCycles(periodTimestamp);
		currentRedistributionDemurrage = toRedistributionDemurrageModifier(currentRedistribution);
		
		currentPeriod = toRedistributionPeriod(currentRedistribution);
		nextRedistribution = toRedistribution(0, toTaxPeriodAmount(currentRedistributionDemurrage, demurrageCounts), totalSupply, currentPeriod + 1);
		redistributions.push(nextRedistribution);

		currentParticipants = toRedistributionParticipants(currentRedistribution);
		if (currentParticipants == 0) {
			currentRemainder = applyDefaultRedistribution(currentRedistribution);
		} else {
			currentRemainder = remainder(currentParticipants, totalSupply); // we can use totalSupply directly because it will always be the same as the recorded supply on the current redistribution
			applyRemainderOnPeriod(currentRemainder, currentPeriod);
		}
		return true;
	}

	// Calculate a value reduced by demurrage by the given period
	// TODO: higher precision
	function toTaxPeriodAmount(uint256 _value, uint256 _period) public view returns (uint256) {
		uint256 valueFactor;
		uint256 truncatedTaxLevel;
	      
		// TODO: if can't get to work, reverse the iteration from current period.
		valueFactor = 1000000;
		truncatedTaxLevel = taxLevel / ppmDivider;

		for (uint256 i = 0; i < _period; i++) {
			valueFactor = valueFactor - ((valueFactor * truncatedTaxLevel) / 1000000);
		}
		return (valueFactor * _value) / 1000000;
	}

	// If the given account is participating in a period and that period has been crossed
	// THEN increase the base value of the account with its share of the value reduction of the period
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
			return false;
		}

		supply = toRedistributionSupply(periodRedistribution);
		baseValue = ((supply / participants) * (taxLevel / 1000000)) / ppmDivider;
		value = toTaxPeriodAmount(baseValue, period - 1);

		//account[_account] &= bytes32(0x000000000000000000000000ffffffffffffffffffffffffffffffffffffffff);
		account[_account] &= bytes32(0xffffffffffffffffffffffffffffffffffffff00000000ffffffffffffffffff);
		increaseBaseBalance(_account, value);

		emit Redistribution(_account, period, value);
		return true;
	}

	// Inflates the given amount according to the current demurrage modifier
	function toBaseAmount(uint256 _value) public view returns (uint256) {
		return (_value * ppmDivider * 1000000) / toDemurrageAmount(demurrageModifier);
	}

	// ERC20, triggers tax and/or redistribution
	function approve(address _spender, uint256 _value) public returns (bool) {
		uint256 baseValue;

		applyDemurrage();
		changePeriod();
		applyRedistributionOnAccount(msg.sender);

		baseValue = toBaseAmount(_value);
		allowance[msg.sender][_spender] += baseValue;
		emit Approval(msg.sender, _spender, _value);
		return true;
	}

	// ERC20, triggers tax and/or redistribution
	function transfer(address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;

		applyDemurrage();
		changePeriod();
		applyRedistributionOnAccount(msg.sender);

		// TODO: Prefer to truncate the result, instead it seems to round to nearest :/
		baseValue = toBaseAmount(_value);
		result = transferBase(msg.sender, _to, baseValue);

		return result;
	}


	// ERC20, triggers tax and/or redistribution
	function transferFrom(address _from, address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;

		applyDemurrage();
		changePeriod();
		applyRedistributionOnAccount(msg.sender);

		baseValue = toBaseAmount(_value);
		require(allowance[_from][msg.sender] >= baseValue);

		result = transferBase(_from, _to, baseValue);
		return result;
	}

	// ERC20 transfer backend for transfer, transferFrom
	function transferBase(address _from, address _to, uint256 _value) private returns (bool) {
		uint256 period;

		decreaseBaseBalance(_from, _value);
		increaseBaseBalance(_to, _value);

		period = actualPeriod();
		if (_value >= minimumParticipantSpend && accountPeriod(_from) != period && _from != _to) {
			registerAccountPeriod(_from, period);
		}
		return true;
	}
}
