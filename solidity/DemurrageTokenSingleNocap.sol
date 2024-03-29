pragma solidity >= 0.8.0;

import "aux/ABDKMath64x64.sol";

// SPDX-License-Identifier: AGPL-3.0-or-later

contract DemurrageTokenSingleNocap {

	struct redistributionItem {
		uint32 period;
		uint72 value;
		uint64 demurrage;
	}
	redistributionItem[] public redistributions;

	// Account balances
	mapping (address => uint256) account;
	
	// Cached demurrage amount, ppm with 38 digit resolution
	//uint128 public demurrageAmount;
	int128 public demurrageAmount;

	// Cached demurrage timestamp; the timestamp for which demurrageAmount was last calculated
	uint256 public demurrageTimestamp;

	// Implements EIP173
	address public owner;

	address newOwner;

	// Implements ERC20
	string public name;

	// Implements ERC20
	string public symbol;

	// Implements ERC20
	uint256 public immutable decimals;

	uint256 supply;

	// Last executed period
	uint256 public lastPeriod;

	// Last sink redistribution amount
	uint256 public totalSink;

	// Value of burnt tokens (burnt tokens do not decay)
	uint256 burned;

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
	//uint256 public immutable decayLevel;
	// 64x64
	int128 public immutable decayLevel;
		
	// Addresses allowed to mint new tokens
	mapping (address => bool) minter;

	// Storage for ERC20 approve/transferFrom methods
	mapping (address => mapping (address => uint256 ) ) allowance; // holder -> spender -> amount (amount is subject to demurrage)

	// Address to send unallocated redistribution tokens
	address public sinkAddress; 

	// timestamp when token contract expires
	uint256 public expires;
	bool expired;

	// supply xap
	uint256 public maxSupply;

	// Implements ERC20
	event Transfer(address indexed _from, address indexed _to, uint256 _value);

	// Implements ERC20
	event Approval(address indexed _owner, address indexed _spender, uint256 _value);

	// Implements Minter
	event Mint(address indexed _minter, address indexed _beneficiary, uint256 _value);

	// New demurrage cache milestone calculated
	event Decayed(uint256 indexed _period, uint256 indexed _periodCount, int128 indexed _oldAmount, int128 _newAmount);

	// When a new period threshold has been crossed
	event Period(uint256 _period);

	// Redistribution applied on a single eligible account
	event Redistribution(address indexed _account, uint256 indexed _period, uint256 _value);

	// Temporary event used in development, will be removed on prod
	//event Debug(bytes32 _foo);
	event Debug(int128 indexed _foo, uint256 indexed _bar);

	// Implements Burn
	event Burn(address indexed _burner, uint256 _value);

	// EIP173
	event OwnershipTransferred(address indexed previousOwner, address indexed newOwner); // EIP173

	// Implements Expire
	event Expired(uint256 _timestamp);

	// Implements Expire
	event ExpiryChange(uint256 indexed _oldTimestamp, uint256 _newTimestamp);

	event Cap(uint256 indexed _oldCap, uint256 _newCap);

	// Implements Seal
	uint256 public sealState;
	uint8 constant WRITER_STATE = 1;
	uint8 constant SINK_STATE = 2;
	uint8 constant EXPIRY_STATE = 4;
	uint8 constant CAP_STATE = 8;
	// Implements Seal
	uint256 constant public maxSealState = 15;

	// Implements Seal
	event SealStateChange(bool indexed _final, uint256 _sealState);


	constructor(string memory _name, string memory _symbol, uint8 _decimals, int128 _decayLevel, uint256 _periodMinutes, address _defaultSinkAddress) {
		require(_decayLevel < (1 << 64));
		redistributionItem memory initialRedistribution;

		//require(ABDKMath64x64.toUInt(_decayLevel) == 0);

		// ACL setup
		owner = msg.sender;

		// ERC20 setup
		name = _name;
		symbol = _symbol;
		decimals = _decimals;

		// Demurrage setup
		demurrageTimestamp = block.timestamp;
		periodStart = demurrageTimestamp;
		periodDuration = _periodMinutes * 60;
		demurrageAmount = ABDKMath64x64.fromUInt(1);

		decayLevel = ABDKMath64x64.ln(_decayLevel);
		initialRedistribution = toRedistribution(0, demurrageAmount, 0, 1);
		redistributions.push(initialRedistribution);

		// Misc settings
		sinkAddress = _defaultSinkAddress;
	}

	function seal(uint256 _state) public returns(uint256) {
		require(_state < 16, 'ERR_INVALID_STATE');
		require(_state & sealState == 0, 'ERR_ALREADY_LOCKED');
		sealState |= _state;
		emit SealStateChange(sealState == maxSealState, sealState);
		return uint256(sealState);
	}

	function isSealed(uint256 _state) public view returns(bool) {
		require(_state < maxSealState);
		if (_state == 0) {
			return sealState == maxSealState;
		}
		return _state & sealState == _state;
	}

	// Set when token expires. 
	// Value is set it terms of redistribution periods.
	// Cannot be set to a time in the past.
	function setExpirePeriod(uint256 _expirePeriod) public {
		uint256 r;
		uint256 oldTimestamp;

		require(!isSealed(EXPIRY_STATE));
		require(!expired);
		require(msg.sender == owner);
		r = periodStart + (_expirePeriod * periodDuration);
		require(r > expires);
		oldTimestamp = expires;
		expires = r;
		emit ExpiryChange(oldTimestamp, expires);
	}

	// Change max token supply.
	// Can only increase supply cap, not decrease.
	function setMaxSupply(uint256 _cap) public {
		require(!isSealed(CAP_STATE));
		require(msg.sender == owner);
		require(_cap > totalSupply());
		emit Cap(maxSupply, _cap);
		maxSupply = _cap;
	}

	// Change sink address for redistribution
	function setSinkAddress(address _sinkAddress) public {
		require(!isSealed(SINK_STATE));
		require(msg.sender == owner);
		sinkAddress = _sinkAddress;
	}

	// Expire the contract if expire is set and we have gone over the threshold.
	// Finalizes demurrage up to the timestamp of the expiry. 
	// The first approve, transfer or transferFrom call that hits the ex == 2 will get the tx mined. but without the actual effect. Otherwise we would have to wait until an external egent called applyExpiry to get the correct final balance.
	// Implements Expire
	function applyExpiry() public returns(uint8) {
		if (expired) {
			return 1;
		}
		if (expires == 0) {
			return 0;
		}
		if (block.timestamp >= expires) {
			applyDemurrageLimited(expires - demurrageTimestamp / 60);
			expired = true;
			emit Expired(block.timestamp);
			changePeriod();
			return 2;
		}
		return 0;
	}

	// Given address will be allowed to call the mintTo() function
	// Implements Writer
	function addWriter(address _minter) public returns (bool) {
		require(!isSealed(WRITER_STATE));
		require(msg.sender == owner);
		minter[_minter] = true;
		return true;
	}

	// Given address will no longer be allowed to call the mintTo() function
	// Implements Writer
	function deleteWriter(address _minter) public returns (bool) {
		require(!isSealed(WRITER_STATE));
		require(msg.sender == owner || _minter == msg.sender);
		minter[_minter] = false;
		return true;
	}

	// Implements Writer
	function isWriter(address _minter) public view returns(bool) {
		return minter[_minter] || _minter == owner;
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
	}

	// Balance unmodified by demurrage
	function baseBalanceOf(address _account) public view returns (uint256) {
		return account[_account];
	}

	/// Increases base balance for a single account
	function increaseBaseBalance(address _account, uint256 _delta) private returns (bool) {
		uint256 oldBalance;
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

	// Send full balance of one account to another
	function sweep(address _account) public returns (uint256) {
		uint256 v;

		v = account[msg.sender];
		account[msg.sender] = 0;
		account[_account] += v;
		emit Transfer(msg.sender, _account, v);
		return v;
	}

	// Creates new tokens out of thin air, and allocates them to the given address
	// Triggers tax
	// Implements Minter
	function mintTo(address _beneficiary, uint256 _amount) public returns (bool) {
		uint256 baseAmount;

		require(applyExpiry() == 0);
		require(minter[msg.sender] || msg.sender == owner, 'ERR_ACCESS');

		changePeriod();
		if (maxSupply > 0) {
			require(supply + _amount <= maxSupply);
		}
		supply += _amount;

		baseAmount = toBaseAmount(_amount);
		increaseBaseBalance(_beneficiary, baseAmount);
		emit Mint(msg.sender, _beneficiary, _amount);
		saveRedistributionSupply();
		return true;
	}

	// Implements Minter
	function mint(address _beneficiary, uint256 _amount, bytes calldata _data) public {
		_data;
		mintTo(_beneficiary, _amount);
	}

	// Implements Minter
	function safeMint(address _beneficiary, uint256 _amount, bytes calldata _data) public {
		_data;
		mintTo(_beneficiary, _amount);
	}

	// Deserializes the redistribution word
	function toRedistribution(uint256 _participants, int128 _demurrageModifier, uint256 _value, uint256 _period) public pure returns(redistributionItem memory) {
		redistributionItem memory redistribution;

		redistribution.period = uint32(_period);
		redistribution.value = uint72(_value);
		redistribution.demurrage = uint64(uint128(_demurrageModifier) & 0xffffffffffffffff);
		_participants;
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
	function toRedistributionDemurrageModifier(redistributionItem memory _redistribution) public pure returns (int128) {
		int128 r;

		r = int128(int64(_redistribution.demurrage) & int128(0x0000000000000000ffffffffffffffff));
		if (r == 0) {
			r = ABDKMath64x64.fromUInt(1);
		}
		return r;
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

	// Retrieve next redistribution if the period threshold has been crossed
	function checkPeriod() private view returns (redistributionItem memory) {
		redistributionItem memory lastRedistribution;
		redistributionItem memory emptyRedistribution;
		uint256 currentPeriod;

		lastRedistribution =  redistributions[lastPeriod];
		currentPeriod = this.actualPeriod();
		if (currentPeriod <= toRedistributionPeriod(lastRedistribution)) {
			return emptyRedistribution;
		}
		return lastRedistribution;
	}

	function getDistribution(uint256 _supply, int128 _demurrageAmount) public pure returns (uint256) {
		int128 difference;

		difference = ABDKMath64x64.mul(ABDKMath64x64.fromUInt(_supply), ABDKMath64x64.sub(ABDKMath64x64.fromUInt(1), _demurrageAmount));
		return _supply - ABDKMath64x64.toUInt(difference);
			
	}

	function getDistributionFromRedistribution(redistributionItem memory _redistribution) public pure returns (uint256) {
		uint256 redistributionSupply;
		int128 redistributionDemurrage;

		redistributionSupply = toRedistributionSupply(_redistribution);
		redistributionDemurrage = toRedistributionDemurrageModifier(_redistribution);
		return getDistribution(redistributionSupply, redistributionDemurrage);
	}

	// Returns the amount sent to the sink address
	function applyDefaultRedistribution(redistributionItem memory _redistribution) private returns (uint256) {
		uint256 unit;
		uint256 baseUnit;
	
		unit = totalSupply() - getDistributionFromRedistribution(_redistribution);	
		baseUnit = toBaseAmount(unit) - totalSink;
		increaseBaseBalance(sinkAddress, baseUnit);
		emit Redistribution(sinkAddress, _redistribution.period, unit);
		lastPeriod += 1;
		totalSink += baseUnit;
		return unit;
	}

	// Recalculate the demurrage modifier for the new period
	// Note that the supply for the consecutive period will be taken at the time of code execution, and thus not necessarily at the time when the redistribution period threshold was crossed.
	function changePeriod() public returns (bool) {
		redistributionItem memory currentRedistribution;
		redistributionItem memory nextRedistribution;
		redistributionItem memory lastRedistribution;
		uint256 currentPeriod;
		int128 lastDemurrageAmount;
		int128 nextRedistributionDemurrage;
		uint256 demurrageCounts;
		uint256 nextPeriod;

		applyDemurrage();
		currentRedistribution = checkPeriod();
		if (isEmptyRedistribution(currentRedistribution)) {
			return false;
		}

		// calculate the decay from previous redistributino
		lastRedistribution = redistributions[lastPeriod];
		currentPeriod = toRedistributionPeriod(currentRedistribution);
		nextPeriod = currentPeriod + 1;
		lastDemurrageAmount = toRedistributionDemurrageModifier(lastRedistribution);
		demurrageCounts = (periodDuration * currentPeriod) / 60;
		// TODO refactor decayby to take int128 then DRY with it
		nextRedistributionDemurrage = ABDKMath64x64.exp(ABDKMath64x64.mul(decayLevel, ABDKMath64x64.fromUInt(demurrageCounts)));
		nextRedistribution = toRedistribution(0, nextRedistributionDemurrage, totalSupply(), nextPeriod);
		redistributions.push(nextRedistribution);

		applyDefaultRedistribution(nextRedistribution);
		emit Period(nextPeriod);
		return true;
	}

	// Calculate the time delta in whole minutes passed between given timestamp and current timestamp
	function getMinutesDelta(uint256 _lastTimestamp) public view returns (uint256) {
		return (block.timestamp - _lastTimestamp) / 60;
	}

	// Calculate and cache the demurrage value corresponding to the (period of the) time of the method call
	function applyDemurrage() public returns (uint256) {
		return applyDemurrageLimited(0);
	}

	// returns true if expired
	function applyDemurrageLimited(uint256 _rounds) public returns (uint256) {
		int128 v;
		uint256 periodCount;
		int128 periodPoint;
		int128 lastDemurrageAmount;

		if (expired) {
			return 0; 
		}

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
		v = ABDKMath64x64.mul(decayLevel, periodPoint);
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

	// Equality check for empty redistribution data
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


	// Calculate a value reduced by demurrage by the given period
	function decayBy(uint256 _value, uint256 _period)  public view returns (uint256) {
		int128 valuePoint;
		int128 periodPoint;
		int128 v;
	
		valuePoint = ABDKMath64x64.fromUInt(_value);
		periodPoint = ABDKMath64x64.fromUInt(_period);

		v = ABDKMath64x64.mul(decayLevel, periodPoint);
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

	// Triggers tax and/or redistribution
	// Implements ERC20
	function approve(address _spender, uint256 _value) public returns (bool) {
		uint256 baseValue;
		uint8 ex;

		ex = applyExpiry();
		if (ex == 2) {
			return false;	
		} else if (ex > 0) {
			revert('EXPIRED');
		}
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

	// Triggers tax and/or redistribution
	// Implements ERC20
	function transfer(address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;
		uint8 ex;

		ex = applyExpiry();
		if (ex == 2) {
			return false;	
		} else if (ex > 0) {
			revert('EXPIRED');
		}
		changePeriod();

		baseValue = toBaseAmount(_value);
		result = transferBase(msg.sender, _to, baseValue);
		emit Transfer(msg.sender, _to, _value);
		return result;
	}

	// Triggers tax and/or redistribution
	// Implements ERC20
	function transferFrom(address _from, address _to, uint256 _value) public returns (bool) {
		uint256 baseValue;
		bool result;
		uint8 ex;

		ex = applyExpiry();
		if (ex == 2) {
			return false;	
		} else if (ex > 0) {
			revert('EXPIRED');
		}
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
		decreaseBaseBalance(_from, _value);
		increaseBaseBalance(_to, _value);

		return true;
	}

	// Implements EIP173
	function transferOwnership(address _newOwner) public returns (bool) {
		address oldOwner;

		require(msg.sender == owner);
		oldOwner = owner;
		owner = _newOwner;

		emit OwnershipTransferred(oldOwner, owner);
		return true;
	}

	// Explicitly and irretrievably burn tokens
	// Only token minters can burn tokens
	// Implements Burner
	function burn(uint256 _value) public returns(bool) {
		require(applyExpiry() == 0);
		require(minter[msg.sender] || msg.sender == owner, 'ERR_ACCESS');
		require(_value <= account[msg.sender]);
		uint256 _delta = toBaseAmount(_value);

		//applyDemurrage();
		decreaseBaseBalance(msg.sender, _delta);
		burned += _value;
		emit Burn(msg.sender, _value);
		return true;
	}

	// Implements Burner
	function burn(address _from, uint256 _value, bytes calldata _data) public {
		require(_from == msg.sender, 'ERR_ONLY_SELF_BURN');
		_data;
		burn(_value);
	}

	// Implements Burner
	function burn() public returns(bool) {
		return burn(account[msg.sender]);
	}

	// Implements ERC20
	function totalSupply() public view returns (uint256) {
		return supply - burned;
	}

	// Return total number of burned tokens
	// Implements Burner
	function totalBurned() public view returns (uint256) {
		return burned;
	}

	// Return total number of tokens ever minted
	// Implements Burner
	function totalMinted() public view returns (uint256) {
		return supply;
	}


	// Implements EIP165
	function supportsInterface(bytes4 _sum) public pure returns (bool) {
		if (_sum == 0xb61bc941) { // ERC20
			return true;
		}
		if (_sum == 0x5878bcf4) { // Minter
			return true;
		}
		if (_sum == 0xbc4babdd) { // Burner
			return true;
		}
		if (_sum == 0x0d7491f8) { // Seal
			return true;
		}
		if (_sum == 0xabe1f1f5) { // Writer
			return true;
		}
		if (_sum == 0x841a0e94) { // Expire
			return true;
		}
		if (_sum == 0x01ffc9a7) { // ERC165
			return true;
		}
		if (_sum == 0x9493f8b2) { // ERC173
			return true;
		}
		if (_sum == 0xd0017968) { // ERC5678Ext20
			return true;
		}
		return false;
	}
}
