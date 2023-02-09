pragma solidity >= 0.8.0;


import "aux/ABDKMath64x64.sol";

// SPDX-License-Identifier: GPL-3.0-or-later
contract DemurrageTokenSingleCap {

	struct redistributionItem {
		uint32 period;
		uint72 value;
		uint40 demurrage;
	}
	redistributionItem[] public redistributions; // uint51(unused) | uint64(demurrageModifier) | uint36(participants) | uint72(value) | uint32(period)

	// Account balances
	mapping (address => uint256) account;
	
	// Cached demurrage amount, ppm with 38 digit resolution
	//uint128 public demurrageAmount;
	int128 public demurrageAmount;

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
	//uint256 constant nanoDivider = 100000000000000000000000000; // now nanodivider, 6 zeros less

	// remaining decimal positions of nanoDivider to reach 38, equals precision in growth and decay
	//uint256 constant growthResolutionFactor = 1000000000000;

	// demurrage decimal width; 38 places
	//uint256 public immutable resolutionFactor = nanoDivider * growthResolutionFactor; 

	// Timestamp of start of periods (time which contract constructor was called)
	uint256 public immutable periodStart;

	// Duration of a single redistribution period in seconds
	uint256 public immutable periodDuration;

	// Demurrage in ppm per minute
	//uint256 public immutable taxLevel;
	// 64x64
	int128 public taxLevel;
		
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
	event Decayed(uint256 indexed _period, uint256 indexed _periodCount, int128 indexed _oldAmount, int128 _newAmount);

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

	constructor(string memory _name, string memory _symbol, uint8 _decimals, int128 _taxLevel, uint256 _periodMinutes, address _defaultSinkAddress) {
		require(_taxLevel < (1 << 64));
		redistributionItem memory initialRedistribution;

		//require(ABDKMath64x64.toUInt(_taxLevel) == 0);

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
		demurrageAmount = ABDKMath64x64.fromUInt(1);

		//taxLevel = ABDKMath64x64.mul(ABDKMath64x64.ln(ABDKMath64x64.sub(demurrageAmount, , ABDKMath64x64.fromUInt(_periodMinutes));
		taxLevel = ABDKMath64x64.ln(_taxLevel);
		initialRedistribution = toRedistribution(0, uint40(uint128(demurrageAmount)), 0, 1);
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
		int128 baseBalance;
		int128 currentDemurragedAmount;
		uint256 periodCount;

		baseBalance = ABDKMath64x64.fromUInt(baseBalanceOf(_account));

		periodCount = getMinutesDelta(demurrageTimestamp);

		currentDemurragedAmount = ABDKMath64x64.mul(baseBalance, demurrageAmount);
		return decayBy(ABDKMath64x64.toUInt(currentDemurragedAmount), periodCount);

		//return (baseBalance * currentDemurragedAmount) / (nanoDivider * 1000000000000);
	}

	// Balance unmodified by demurrage
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

	function changePeriod() public {
		applyDemurrage();	
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
	function toRedistribution(uint256 _participants, uint256 _demurrageModifierPpm, uint256 _value, uint256 _period) public pure returns(redistributionItem memory) {
		redistributionItem memory redistribution;

		redistribution.period = uint32(_period);
		redistribution.value = uint72(_value);
		redistribution.demurrage = uint40(_demurrageModifierPpm);
		return redistribution;

	}

	// Serializes the demurrage period part of the redistribution word
	function toRedistributionPeriod(redistributionItem memory _redistribution) public pure returns (uint256) {
		return uint256(_redistribution.period);
	}

	// Serializes the supply part of the redistribution word
	function toRedistributionSupply(redistributionItem memory _redistribution) public pure returns (uint256) {
		return uint256(_redistribution.value);
	}

	// Serializes the number of participants part of the redistribution word
	function toRedistributionDemurrageModifier(redistributionItem memory _redistribution) public pure returns (uint256) {
		return uint256(_redistribution.demurrage);
	}


	// Client accessor to the redistributions array length
	function redistributionCount() public view returns (uint256) {
		return redistributions.length;
	}

	// Save the current total supply amount to the current redistribution period
	function saveRedistributionSupply() private returns (bool) {
		redistributionItem memory currentRedistribution;
		uint256 grownSupply;

		grownSupply = totalSupply();
		currentRedistribution = redistributions[redistributions.length-1];
		currentRedistribution.value = uint72(grownSupply);

		redistributions[redistributions.length-1] = currentRedistribution;
		return true;
	}

	// Get the demurrage period of the current block number
	function actualPeriod() public view returns (uint128) {
		return uint128((block.timestamp - periodStart) / periodDuration + 1);
	}

//	// Retrieve next redistribution if the period threshold has been crossed
//	function checkPeriod() private view returns (redistributionItem memory) {
//		redistributionItem memory lastRedistribution;
//		redistributionItem memory emptyRedistribution;
//		uint256 currentPeriod;
//
//		lastRedistribution =  redistributions[lastPeriod];
//		currentPeriod = this.actualPeriod();
//		if (currentPeriod <= toRedistributionPeriod(lastRedistribution)) {
//			return emptyRedistribution;
//		}
//		return lastRedistribution;
//	}

//	function getDistribution(uint256 _supply, uint256 _demurrageAmount) public view returns (uint256) {
//		uint256 difference;
//
//		difference = _supply * (resolutionFactor - (_demurrageAmount * 10000000000));
//		return difference / resolutionFactor;
//	}

//	function getDistributionFromRedistribution(redistributionItem memory _redistribution) public returns (uint256) {
//		uint256 redistributionSupply;
//		uint256 redistributionDemurrage;
//
//		redistributionSupply = toRedistributionSupply(_redistribution);
//		redistributionDemurrage = toRedistributionDemurrageModifier(_redistribution);
//		return getDistribution(redistributionSupply, redistributionDemurrage);
//	}
//
//	// Returns the amount sent to the sink address
//	function applyDefaultRedistribution(redistributionItem memory _redistribution) private returns (uint256) {
//		uint256 unit;
//		uint256 baseUnit;
//	
//		unit = getDistributionFromRedistribution(_redistribution);	
//		baseUnit = toBaseAmount(unit) - totalSink;
//		increaseBaseBalance(sinkAddress, baseUnit);
//		lastPeriod += 1;
//		totalSink += baseUnit;
//		return unit;
//	}

	// Calculate the time delta in whole minutes passed between given timestamp and current timestamp
	function getMinutesDelta(uint256 _lastTimestamp) public view returns (uint256) {
		return (block.timestamp - _lastTimestamp) / 60;
	}

	// Calculate and cache the demurrage value corresponding to the (period of the) time of the method call
	function applyDemurrage() public returns (uint256) {
		return applyDemurrageLimited(0);
	}

	function applyDemurrageLimited(uint256 _rounds) public returns (uint256) {
		int128 v;
		uint256 periodCount;
		int128 periodPoint;
		int128 lastDemurrageAmount;

		periodCount = getMinutesDelta(demurrageTimestamp);
		if (periodCount == 0) {
			return 0;
		}
		lastDemurrageAmount = demurrageAmount;
	
		// safety limit for exponential calculation to ensure that we can always
		// execute this code no matter how much time passes.			
		if (_rounds > 0 && _rounds < periodCount) {
			periodCount = _rounds;
		}

		periodPoint = ABDKMath64x64.fromUInt(periodCount);
		v = ABDKMath64x64.mul(taxLevel, periodPoint);
		v = ABDKMath64x64.exp(v);

		demurrageAmount = ABDKMath64x64.mul(demurrageAmount, v);
		demurrageTimestamp = demurrageTimestamp + (periodCount * 60);
		emit Decayed(demurrageTimestamp, periodCount, lastDemurrageAmount, demurrageAmount);
		return periodCount;
	}

	// Return timestamp of start of period threshold
	function getPeriodTimeDelta(uint256 _periodCount) public view returns (uint256) {
		return periodStart + (_periodCount * periodDuration);
	}

	// Amount of demurrage cycles inbetween the current timestamp and the given target time
	function demurrageCycles(uint256 _target) public view returns (uint256) {
		return (block.timestamp - _target) / 60;
	}

	function isEmptyRedistribution(redistributionItem memory _redistribution) public pure returns(bool) {
		if (_redistribution.period > 0) {
			return false;
		}
		if (_redistribution.value > 0) {
			return false;
		}
		if (_redistribution.demurrage > 0) {
			return false;
		}
		return true;
	}

//	// Recalculate the demurrage modifier for the new period
//	// Note that the supply for the consecutive period will be taken at the time of code execution, and thus not necessarily at the time when the redistribution period threshold was crossed.
//	function changePeriod() public returns (bool) {
//		redistributionItem memory currentRedistribution;
//		redistributionItem memory nextRedistribution;
//		redistributionItem memory lastRedistribution;
//		uint256 currentPeriod;
//		uint256 lastDemurrageAmount;
//		uint256 nextRedistributionDemurrage;
//		uint256 demurrageCounts;
//		uint256 nextPeriod;
//
//		applyDemurrage();
//		currentRedistribution = checkPeriod();
//		if (isEmptyRedistribution(currentRedistribution)) {
//			return false;
//		}
//
//		// calculate the decay from previous redistributino
//		lastRedistribution = redistributions[lastPeriod];
//		currentPeriod = toRedistributionPeriod(currentRedistribution);
//		nextPeriod = currentPeriod + 1;
//		lastDemurrageAmount = toRedistributionDemurrageModifier(lastRedistribution);
//		demurrageCounts = periodDuration / 60;
//		nextRedistributionDemurrage = decayBy(lastDemurrageAmount, demurrageCounts);
//	
//		nextRedistribution = toRedistribution(0, nextRedistributionDemurrage, totalSupply(), nextPeriod);
//		redistributions.push(nextRedistribution);
//
//		applyDefaultRedistribution(nextRedistribution);
//		emit Period(nextPeriod);
//		return true;
//	}
//
//	// Reverse a value reduced by demurrage by the given period to its original value
////	function growBy(uint256 _value, uint256 _period) public view returns (uint256) {
////		uint256 valueFactor;
////		uint256 truncatedTaxLevel;
////	      
////		valueFactor = growthResolutionFactor;
////		truncatedTaxLevel = taxLevel / nanoDivider;
////
////		for (uint256 i = 0; i < _period; i++) {
////			valueFactor = valueFactor + ((valueFactor * truncatedTaxLevel) / growthResolutionFactor);
////		}
////		return (valueFactor * _value) / growthResolutionFactor;
////	}

	// Calculate a value reduced by demurrage by the given period
	function decayBy(uint256 _value, uint256 _period)  public view returns (uint256) {
		int128 valuePoint;
		int128 periodPoint;
		int128 v;
	
		valuePoint = ABDKMath64x64.fromUInt(_value);
		periodPoint = ABDKMath64x64.fromUInt(_period);

		v = ABDKMath64x64.mul(taxLevel, periodPoint);
		v = ABDKMath64x64.exp(v);
		v = ABDKMath64x64.mul(valuePoint, v);
		return ABDKMath64x64.toUInt(v);
	}


	// Inflates the given amount according to the current demurrage modifier
	function toBaseAmount(uint256 _value) public view returns (uint256) {
		int128 r;
		r = ABDKMath64x64.div(ABDKMath64x64.fromUInt(_value), demurrageAmount);
		return ABDKMath64x64.toUInt(r);
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
		require(_value <= account[msg.sender]);
		uint256 _delta = toBaseAmount(_value);

		//applyDemurrage();
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
