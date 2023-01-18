pragma solidity >= 0.8.0;

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
	uint256 constant maskRedistributionDemurrage	= 0x0000000000ffffffffffffffffffffffffffff00000000000000000000000000; // ((1 << 36) - 1) << 140

	// Account balances
	mapping (address => bytes32[] ) account;
	uint8 constant shiftAccountValue		= 0;
	uint256 constant maskAccountValue 		= 0x0000000000000000000000000000000000000000000000ffffffffffffffffff; // (1 << 72) - 1
	uint8 constant shiftAccountPeriod		= 72;
	uint256 constant maskAccountPeriod 		= 0x00000000000000000000000000000000000000ffffffff000000000000000000; // ((1 << 32) - 1) << 72
	uint8 constant shiftAccountUsed			= 255;
	uint256 constant maskAccountUsed 		= 0x8000000000000000000000000000000000000000000000000000000000000000; // (1 << 255)
	
	// Cached demurrage amount, ppm with 38 digit resolution
	uint128 public demurrageAmount;

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
	//uint256 public totalSupply;
	uint256 supply;

	// Last executed period
	uint256 public lastPeriod;

	// Last sink redistribution amount
	uint256 public totalSink;

	// Value of burnt tokens (burnt tokens do not decay)
	uint256 public burned;

	// 128 bit resolution of the demurrage divisor
	// (this constant x 1000000 is contained within 128 bits)
	uint256 constant nanoDivider = 100000000000000000000000000; // now nanodivider, 6 zeros less

	// remaining decimal positions of nanoDivider to reach 38, equals precision in growth and decay
	uint256 constant growthResolutionFactor = 1000000000000;

	// demurrage decimal width; 38 places
	uint256 public immutable resolutionFactor = nanoDivider * growthResolutionFactor; 

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
	address public sinkAddress; 

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

	// Emitted when tokens are burned
	event Burn(address indexed _burner, uint256 _value);

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
		demurrageAmount = uint128(nanoDivider) * 100;
		taxLevel = _taxLevelMinute; // Represents 38 decimal places
		bytes32 initialRedistribution = toRedistribution(0, demurrageAmount, 0, 1);
		redistributions.push(initialRedistribution);

		// Misc settings
		sinkAddress = _defaultSinkAddress;
	}


	// Change sink address for redistribution
	function setSinkAddress(address _sinkAddress) public {
		require(msg.sender == owner);
		sinkAddress = _sinkAddress;
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

		periodCount = getMinutesDelta(demurrageTimestamp);

		currentDemurragedAmount = uint128(decayBy(demurrageAmount * 10000000000, periodCount));

		return (baseBalance * currentDemurragedAmount) / (nanoDivider * 1000000000000);
	}


	/// Balance unmodified by demurrage
	function baseBalanceOf(address _account) public view returns (uint256) {
		uint256 lastPeriodUsed;

		lastPeriodUsed = account[_account].length;
		if (lastPeriodUsed == 0) {
			return 0;
		}
		return uint256(account[_account][lastPeriodUsed]) & maskAccountValue;
	}


	/// Increases base balance for a single account
	function increaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		if (_delta == 0) {
			return false;
		}
		
		movePeriodBalance(_account, int256(_delta));
		return true;
	}

	/// Decreases base balance for a single account
	function decreaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		if (_delta == 0) {
			return false;
		}

		movePeriodBalance(_account, int256(_delta) * -1);
		return true;
	}

	// Creates new tokens out of thin air, and allocates them to the given address
	// Triggers tax
	function mintTo(address _beneficiary, uint256 _amount) external returns (bool) {
		uint256 baseAmount;

		require(minter[msg.sender], 'ERR_ACCESS');

		changePeriod();
		baseAmount = toBaseAmount(_amount);
		supply += _amount;
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

		grownSupply = totalSupply();
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

	// Retrieve next redistribution if the period threshold has been crossed
	function checkPeriod() private view returns (bytes32) {
		bytes32 lastRedistribution;
		uint256 currentPeriod;

		lastRedistribution =  redistributions[lastPeriod];
		currentPeriod = this.actualPeriod();
		if (currentPeriod <= toRedistributionPeriod(lastRedistribution)) {
			return bytes32(0x00);
		}
		return lastRedistribution;
	}

	function getDistribution(uint256 _supply, uint256 _demurrageAmount) public view returns (uint256) {
		uint256 difference;

		difference = _supply * (resolutionFactor - (_demurrageAmount * 10000000000));
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
		uint256 baseUnit;
	
		unit = getDistributionFromRedistribution(_redistribution);	
		baseUnit = toBaseAmount(unit) - totalSink;
		increaseBaseBalance(sinkAddress, baseUnit);
		lastPeriod += 1;
		totalSink += baseUnit;
		return unit;
	}

	// Calculate the time delta in whole minutes passed between given timestamp and current timestamp
	function getMinutesDelta(uint256 _lastTimestamp) public view returns (uint256) {
		return (block.timestamp - _lastTimestamp) / 60;
	}

	// Calculate and cache the demurrage value corresponding to the (period of the) time of the method call
	function applyDemurrage() public returns (bool) {
		return applyDemurrageLimited(0);
	}

	function applyDemurrageLimited(uint256 _rounds) public returns (bool) {
		uint256 periodCount;
		uint256 lastDemurrageAmount;

		periodCount = getMinutesDelta(demurrageTimestamp);
		if (periodCount == 0) {
			return false;
		}
		lastDemurrageAmount = demurrageAmount;
	
		// safety limit for exponential calculation to ensure that we can always
		// execute this code no matter how much time passes.			
		if (_rounds > 0 && _rounds < periodCount) {
			periodCount = _rounds;
		}

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


	// Deserialize the pemurrage period for the given account is participating in
	function accountPeriod(address _account) public view returns (uint256) {
		uint256 accountPeriods;

		accountPeriods = account[_account].length;
		if (accountPeriods == 0) {
			return 0;
		}
		return accountPeriodBase(_account, accountPeriods - 1);
	}

	function accountPeriodBase(address _account, uint256 _idx) private view returns (uint256) {
		return (uint256(account[_account][_idx]) & maskAccountPeriod) >> shiftAccountPeriod;
	}

	function movePeriodBalance(address _account, int256 _delta) private {
		int256 oldBalance;
		uint256 newBalance;
		uint256 workAccount;

		//workAccount = uint256(account[_index][_account]);

		oldBalance = int256(baseBalanceOf(_account));
		newBalance = uint256(oldBalance + _delta);
		require(uint72(newBalance) > uint72(uint256(oldBalance)), 'ERR_WOULDWRAP'); // revert if increase would result in a wrapped value
		workAccount = (1 << 255);

		workAccount |= ((uint32(lastPeriod) << shiftAccountPeriod) & maskAccountPeriod);
		workAccount |= (baseBalanceOf(_account) & maskAccountValue);
		account[_account].push(bytes32(workAccount));
	}

	function registerAccountPeriod(address _account, int256 _delta) public {
		uint256 accountPeriods;
		uint256 lastPeriodUsed;

		accountPeriods = account[_account].length;
		if (lastPeriodUsed == 0) {
			account[_account].push(bytes32(uint256(_delta) | (1 << 255)));
			return;
		}
		lastPeriodUsed = accountPeriodBase(_account, accountPeriods - 1);
		if (lastPeriodUsed != lastPeriod) {
			movePeriodBalance(_account, _delta);
		}
	}

	// Recalculate the demurrage modifier for the new period
	// Note that the supply for the consecutive period will be taken at the time of code execution, and thus not necessarily at the time when the redistribution period threshold was crossed.
	function changePeriod() public returns (bool) {
		bytes32 currentRedistribution;
		bytes32 nextRedistribution;
		uint256 currentPeriod;
		uint256 lastDemurrageAmount;
		bytes32 lastRedistribution;
		uint256 nextRedistributionDemurrage;
		uint256 demurrageCounts;
		uint256 nextPeriod;

		applyDemurrage();
		currentRedistribution = checkPeriod();
		if (currentRedistribution == bytes32(0x00)) {
			return false;
		}

		// calculate the decay from previous redistributino
		lastRedistribution = redistributions[lastPeriod];
		currentPeriod = toRedistributionPeriod(currentRedistribution);
		nextPeriod = currentPeriod + 1;
		lastDemurrageAmount = toRedistributionDemurrageModifier(lastRedistribution);
		demurrageCounts = periodDuration / 60;
		nextRedistributionDemurrage = decayBy(lastDemurrageAmount, demurrageCounts);
	
		nextRedistribution = toRedistribution(0, nextRedistributionDemurrage, totalSupply(), nextPeriod);
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
		return (_value * resolutionFactor) / (demurrageAmount * 10000000000);
	}

	// Implements ERC20, triggers tax and/or redistribution
	function approve(address _spender, uint256 _value) public returns (bool) {
		uint256 baseValue;

		if (allowance[msg.sender][_spender] > 0) {
			require(_value == 0, 'ZERO_FIRST');
		}
		
		changePeriod();

		baseValue = toBaseAmount(_value);
		allowance[msg.sender][_spender] = baseValue;
		emit Approval(msg.sender, _spender, _value);
		return true;
	}

	// Reduce allowance by amount
	function decreaseAllowance(address _spender, uint256 _value) public returns (bool) {
		uint256 baseValue;

		baseValue = toBaseAmount(_value);
		require(allowance[msg.sender][_spender] >= baseValue);
		
		changePeriod();

		allowance[msg.sender][_spender] -= baseValue;
		emit Approval(msg.sender, _spender, allowance[msg.sender][_spender]);
		return true;
	}

	// Increase allowance by amount
	function increaseAllowance(address _spender, uint256 _value) public returns (bool) {
		uint256 baseValue;

		changePeriod();

		baseValue = toBaseAmount(_value);

		allowance[msg.sender][_spender] += baseValue;
		emit Approval(msg.sender, _spender, allowance[msg.sender][_spender]);
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

		allowance[_from][msg.sender] -= baseValue;
		result = transferBase(_from, _to, baseValue);

		emit Transfer(_from, _to, _value);
		return result;
	}

	// ERC20 transfer backend for transfer, transferFrom
	function transferBase(address _from, address _to, uint256 _value) private returns (bool) {
		uint256 period;

		decreaseBaseBalance(_from, _value);
		increaseBaseBalance(_to, _value);

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

	// Explicitly and irretrievably burn tokens
	// Only token minters can burn tokens
	function burn(uint256 _value) public {
		require(minter[msg.sender]);
		require(_value <= balanceOf(msg.sender));
		uint256 _delta = toBaseAmount(_value);

		applyDemurrage();
		decreaseBaseBalance(msg.sender, _delta);
		burned += _value;
		emit Burn(msg.sender, _value);
	}

	// Implements ERC20
	function totalSupply() public view returns (uint256) {
		return supply - burned;
	}

	// Return total number of burned tokens
	function totalBurned() public view returns (uint256) {
		return burned;
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
