pragma solidity > 0.6.11;

// SPDX-License-Identifier: GPL-3.0-or-later

contract DemurrageTokenSingleCap {

	// Redistribution bit field, with associated shifts and masks
	// (Uses sub-byte boundaries)
	bytes32[] public redistributions; // uint51(unused) | uint64(demurrageModifier) | uint36(participants) | uint72(value) | uint32(period)
	uint8 constant shiftRedistributionPeriod 	= 0;
	uint256 constant maskRedistributionPeriod 	= 0x00000000000000000000000000000000000000000000000000000000ffffffff; // (1 << 32) - 1
	uint8 constant shiftRedistributionValue 	= 32;
	uint256 constant maskRedistributionValue	= 0x00000000000000000000000000000000000000ffffffffffffffffff00000000; // ((1 << 72) - 1) << 32
	uint8 constant shiftRedistributionDemurrage	= 104;
	uint256 constant maskRedistributionDemurrage	= 0x000000ffffffffffffffffffffffffffffffff00000000000000000000000000; // ((1 << 20) - 1) << 140

	uint8 constant shiftRedistributionIsUsed	= 255;
	uint256 constant maskRedistributionIsUsed	= 0x4000000000000000000000000000000000000000000000000000000000000000; // 1 << 255


	// Account balances
	mapping (address => uint256) account;
	
	// Cached demurrage amount, ppm with 38 digit resolution
	uint128 public demurrageAmount;

	// Cached demurrage period; the period for which demurrageAmount was calculated
	//uint128 public demurragePeriod;
	// Cached demurrage timestamp; the timestamp for which demurrageAmount was last calculated
	uint256 public demurrageTimestamp;

	// Implements EIP172
	address public owner;

	address newOwner;

	// Implements ERC20
	string public name;

	// Implements ERC20
	string public symbol;

	// Implements ERC20
	uint256 public decimals;

	// Implements ERC20
	uint256 public totalSupply;

	// Minimum amount of (demurraged) tokens an account must spend to participate in redistribution for a particular period
	uint256 public minimumParticipantSpend;

	// 128 bit resolution of the demurrage divisor
	// (this constant x 1000000 is contained within 128 bits)
	uint256 constant nanoDivider = 100000000000000000000000000; // now nanodivider, 6 zeros less

	// remaining decimal positions of nanoDivider to reach 38, equals precision in growth and decay
	uint256 constant growthResolutionFactor = 1000000000000;

	// demurrage decimal width; 38 places
	uint256 immutable resolutionFactor = nanoDivider * growthResolutionFactor; 

	// Timestamp of start of periods (time which contract constructor was called)
	uint256 public immutable periodStart;

	// Duration of a single redistribution period in seconds
	uint256 public immutable periodDuration;

	// Demurrage in ppm per minute
	uint256 public immutable taxLevel;
		
	// Addresses allowed to mint new tokens
	mapping (address => bool) minter;

	// Storage for ERC20 approve/transferFrom methods
	mapping (address => mapping (address => uint256 ) ) allowance; // holder -> spender -> amount (amount is subject to demurrage)

	// Address to send unallocated redistribution tokens
	address sinkAddress; 

	// Implements ERC20
	event Transfer(address indexed _from, address indexed _to, uint256 _value);

	// Implements ERC20
	event Approval(address indexed _owner, address indexed _spender, uint256 _value);

	// New tokens minted
	event Mint(address indexed _minter, address indexed _beneficiary, uint256 _value);

	// New demurrage cache milestone calculated
	event Decayed(uint256 indexed _period, uint256 indexed _periodCount, uint256 indexed _oldAmount, uint256 _newAmount);

	// When a new period threshold has been crossed
	event Period(uint256 _period);

	// Redistribution applied on a single eligible account
	event Redistribution(address indexed _account, uint256 indexed _period, uint256 _value);

	// Temporary event used in development, will be removed on prod
	event Debug(bytes32 _foo);

	// EIP173
	event OwnershipTransferred(address indexed previousOwner, address indexed newOwner); // EIP173

	constructor(string memory _name, string memory _symbol, uint8 _decimals, uint128 _taxLevelMinute, uint256 _periodMinutes, address _defaultSinkAddress) public {
		// ACL setup
		owner = msg.sender;
		minter[owner] = true;

		// ERC20 setup
		name = _name;
		symbol = _symbol;
		decimals = _decimals;

		// Demurrage setup
		demurrageTimestamp = block.timestamp;
		periodStart = demurrageTimestamp;
		periodDuration = _periodMinutes * 60;
		//demurrageAmount = 100000000000000000000000000000000000000 - _taxLevelMinute; // Represents 38 decimal places, same as resolutionFactor
		demurrageAmount = 100000000000000000000000000000000000000;
		//demurragePeriod = 1;
		taxLevel = _taxLevelMinute; // Represents 38 decimal places
		bytes32 initialRedistribution = toRedistribution(0, demurrageAmount, 0, 1);
		redistributions.push(initialRedistribution);

		// Misc settings
		sinkAddress = _defaultSinkAddress;
		minimumParticipantSpend = 10 ** uint256(_decimals);
	}

	// Given address will be allowed to call the mintTo() function
	function addMinter(address _minter) public returns (bool) {
		require(msg.sender == owner);
		minter[_minter] = true;
		return true;
	}

	// Given address will no longer be allowed to call the mintTo() function
	function removeMinter(address _minter) public returns (bool) {
		require(msg.sender == owner || _minter == msg.sender);
		minter[_minter] = false;
		return true;
	}

	/// Implements ERC20
	function balanceOf(address _account) public view returns (uint256) {
		uint256 baseBalance;
		uint256 currentDemurragedAmount;
		uint256 periodCount;

		baseBalance = baseBalanceOf(_account);

		//periodCount = actualPeriod() - demurragePeriod; 
		periodCount = getMinutesDelta(demurrageTimestamp);

		currentDemurragedAmount = uint128(decayBy(demurrageAmount, periodCount));

		return (baseBalance * currentDemurragedAmount) / (nanoDivider * 1000000000000);
	}

	/// Balance unmodified by demurrage
	function baseBalanceOf(address _account) public view returns (uint256) {
		return account[_account];
	}

	/// Increases base balance for a single account
	function increaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
		uint256 newBalance;
		uint256 workAccount;

		workAccount = uint256(account[_account]);
	
		if (_delta == 0) {
			return false;
		}

		oldBalance = baseBalanceOf(_account);
		account[_account] = oldBalance + _delta;
		return true;
	}

	/// Decreases base balance for a single account
	function decreaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
	       	uint256 newBalance;
		uint256 workAccount;

		workAccount = uint256(account[_account]);

		if (_delta == 0) {
			return false;
		}

		oldBalance = baseBalanceOf(_account);	
		require(oldBalance >= _delta, 'ERR_OVERSPEND'); // overspend guard
		account[_account] = oldBalance - _delta;
		return true;
	}

	// Creates new tokens out of thin air, and allocates them to the given address
	// Triggers tax
	function mintTo(address _beneficiary, uint256 _amount) external returns (bool) {
		uint256 baseAmount;

		require(minter[msg.sender], 'ERR_ACCESS');

		changePeriod();
		baseAmount = toBaseAmount(_amount);
		totalSupply += _amount;
		increaseBaseBalance(_beneficiary, baseAmount);
		emit Mint(msg.sender, _beneficiary, _amount);
		saveRedistributionSupply();
		return true;
	}

	// Deserializes the redistribution word
	// uint95(unused) | uint20(demurrageModifier) | uint36(participants) | uint72(value) | uint32(period)
	function toRedistribution(uint256 _participants, uint256 _demurrageModifierPpm, uint256 _value, uint256 _period) public pure returns(bytes32) {
		bytes32 redistribution;

		redistribution |= bytes32((_demurrageModifierPpm << shiftRedistributionDemurrage) & maskRedistributionDemurrage);
		redistribution |= bytes32((_value << shiftRedistributionValue) & maskRedistributionValue); 
		redistribution |= bytes32(_period & maskRedistributionPeriod);
		return redistribution;
	}

	// Serializes the demurrage period part of the redistribution word
	function toRedistributionPeriod(bytes32 redistribution) public pure returns (uint256) {
		return uint256(redistribution) & maskRedistributionPeriod;
	}

	// Serializes the supply part of the redistribution word
	function toRedistributionSupply(bytes32 redistribution) public pure returns (uint256) {
		return (uint256(redistribution) & maskRedistributionValue) >> shiftRedistributionValue;
	}

	// Serializes the number of participants part of the redistribution word
	function toRedistributionDemurrageModifier(bytes32 redistribution) public pure returns (uint256) {
		return (uint256(redistribution) & maskRedistributionDemurrage) >> shiftRedistributionDemurrage;
	}

	// Client accessor to the redistributions array length
	function redistributionCount() public view returns (uint256) {
		return redistributions.length;
	}

	// Save the current total supply amount to the current redistribution period
	function saveRedistributionSupply() private returns (bool) {
		uint256 currentRedistribution;
		uint256 grownSupply;

		//grownSupply = growBy(totalSupply, 1);
		grownSupply = totalSupply;
		currentRedistribution = uint256(redistributions[redistributions.length-1]);
		currentRedistribution &= (~maskRedistributionValue);
		currentRedistribution |= (grownSupply << shiftRedistributionValue);

		redistributions[redistributions.length-1] = bytes32(currentRedistribution);
		return true;
	}

	// Get the demurrage period of the current block number
	function actualPeriod() public view returns (uint128) {
		return uint128((block.timestamp - periodStart) / periodDuration + 1);
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

	function getDistribution(uint256 _supply, uint256 _demurrageAmount) public view returns (uint256) {
		uint256 difference;

		difference = _supply * (resolutionFactor - _demurrageAmount); //(nanoDivider - ((resolutionFactor - _demurrageAmount) / nanoDivider));
		return difference / resolutionFactor;
	}

	function getDistributionFromRedistribution(bytes32 _redistribution) public returns (uint256) {
		uint256 redistributionSupply;
		uint256 redistributionDemurrage;

		redistributionSupply = toRedistributionSupply(_redistribution);
		redistributionDemurrage = toRedistributionDemurrageModifier(_redistribution);
		return getDistribution(redistributionSupply, redistributionDemurrage);
	}

	// Returns the amount sent to the sink address
	function applyDefaultRedistribution(bytes32 _redistribution) private returns (uint256) {
		uint256 unit;
	
		unit = getDistributionFromRedistribution(_redistribution);	
		increaseBaseBalance(sinkAddress, toBaseAmount(unit));
		return unit;
	}

	// Calculate the time delta in whole minutes passed between given timestamp and current timestamp
	function getMinutesDelta(uint256 _lastTimestamp) public view returns (uint256) {
		return (block.timestamp - _lastTimestamp) / 60;
	}

	// Calculate and cache the demurrage value corresponding to the (period of the) time of the method call
	function applyDemurrage() public returns (bool) {
		//uint128 epochPeriodCount;
		uint256 periodCount;
		uint256 lastDemurrageAmount;

		//epochPeriodCount = actualPeriod();
		//periodCount = epochPeriodCount - demurragePeriod;

		periodCount = getMinutesDelta(demurrageTimestamp);
		if (periodCount == 0) {
			return false;
		}
		lastDemurrageAmount = demurrageAmount;
		demurrageAmount = uint128(decayBy(lastDemurrageAmount, periodCount));
		//demurragePeriod = epochPeriodCount; 
		demurrageTimestamp = demurrageTimestamp + (periodCount * 60);
		emit Decayed(demurrageTimestamp, periodCount, lastDemurrageAmount, demurrageAmount);
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
	function changePeriod() public returns (bool) {
		bytes32 currentRedistribution;
		bytes32 nextRedistribution;
		uint256 currentPeriod;
		uint256 currentDemurrageAmount;
		uint256 nextRedistributionDemurrage;
		uint256 demurrageCounts;
		uint256 periodTimestamp;
		uint256 nextPeriod;

		applyDemurrage();
		currentRedistribution = checkPeriod();
		if (currentRedistribution == bytes32(0x00)) {
			return false;
		}

		currentPeriod = toRedistributionPeriod(currentRedistribution);
		nextPeriod = currentPeriod + 1;
		periodTimestamp = getPeriodTimeDelta(currentPeriod);

		currentDemurrageAmount = demurrageAmount; 

		demurrageCounts = demurrageCycles(periodTimestamp);
		if (demurrageCounts > 0) {
			nextRedistributionDemurrage = growBy(currentDemurrageAmount, demurrageCounts);
		} else {
			nextRedistributionDemurrage = currentDemurrageAmount;
		}
		
		nextRedistribution = toRedistribution(0, nextRedistributionDemurrage, totalSupply, nextPeriod);
		redistributions.push(nextRedistribution);

		applyDefaultRedistribution(nextRedistribution);
		emit Period(nextPeriod);
		return true;
	}

	// Reverse a value reduced by demurrage by the given period to its original value
	function growBy(uint256 _value, uint256 _period) public view returns (uint256) {
		uint256 valueFactor;
		uint256 truncatedTaxLevel;
	      
		valueFactor = growthResolutionFactor;
		truncatedTaxLevel = taxLevel / nanoDivider;

		for (uint256 i = 0; i < _period; i++) {
			valueFactor = valueFactor + ((valueFactor * truncatedTaxLevel) / growthResolutionFactor);
		}
		return (valueFactor * _value) / growthResolutionFactor;
	}

	// Calculate a value reduced by demurrage by the given period
	function decayBy(uint256 _value, uint256 _period) public view returns (uint256) {
		uint256 valueFactor;
		uint256 truncatedTaxLevel;
	      
		valueFactor = growthResolutionFactor;
		truncatedTaxLevel = taxLevel / nanoDivider;

		for (uint256 i = 0; i < _period; i++) {
			valueFactor = valueFactor - ((valueFactor * truncatedTaxLevel) / growthResolutionFactor);
		}
		return (valueFactor * _value) / growthResolutionFactor;
	}

	// Inflates the given amount according to the current demurrage modifier
	function toBaseAmount(uint256 _value) public view returns (uint256) {
		return (_value * resolutionFactor) / demurrageAmount;
	}

	// Implements ERC20, triggers tax and/or redistribution
	function approve(address _spender, uint256 _value) public returns (bool) {
		uint256 baseValue;

		changePeriod();

		baseValue = toBaseAmount(_value);
		allowance[msg.sender][_spender] += baseValue;
		emit Approval(msg.sender, _spender, _value);
		return true;
	}

	// Implements ERC20, triggers tax and/or redistribution
	function transfer(address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;

		changePeriod();

		baseValue = toBaseAmount(_value);
		result = transferBase(msg.sender, _to, baseValue);
		emit Transfer(msg.sender, _to, _value);
		return result;
	}

	// Implements ERC20, triggers tax and/or redistribution
	function transferFrom(address _from, address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;

		changePeriod();

		baseValue = toBaseAmount(_value);
		require(allowance[_from][msg.sender] >= baseValue);

		result = transferBase(_from, _to, baseValue);
		emit Transfer(_from, _to, _value);
		return result;
	}

	// ERC20 transfer backend for transfer, transferFrom
	function transferBase(address _from, address _to, uint256 _value) private returns (bool) {
		uint256 period;

		decreaseBaseBalance(_from, _value);
		increaseBaseBalance(_to, _value);

		//period = actualPeriod();
		return true;
	}

	// Implements EIP173
	function transferOwnership(address _newOwner) public returns (bool) {
		require(msg.sender == owner);
		newOwner = _newOwner;
	}

	// Implements OwnedAccepter
	function acceptOwnership() public returns (bool) {
		address oldOwner;

		require(msg.sender == newOwner);
		oldOwner = owner; 
		owner = newOwner;
		newOwner = address(0);
		emit OwnershipTransferred(oldOwner, owner);
	}

	// Implements EIP165
	function supportsInterface(bytes4 _sum) public pure returns (bool) {
		if (_sum == 0xc6bb4b70) { // ERC20
			return true;
		}
		if (_sum == 0x449a52f8) { // Minter
			return true;
		}
		if (_sum == 0x01ffc9a7) { // EIP165
			return true;
		}
		if (_sum == 0x9493f8b2) { // EIP173
			return true;
		}
		if (_sum == 0x37a47be4) { // OwnedAccepter
			return true;
		}
		return false;
	}
}
