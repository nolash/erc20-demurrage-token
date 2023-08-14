# Overview

    de-mur-rage

    1: the detention of a ship by the freighter beyond the time allowed for loading, unloading, or sailing

    2: a charge for detaining a ship, freight car, or truck

This ERC20 smart contract implementation for the EVM imposes a demurrage
on all held token balances.

The demurrage is a continuous value *decay*, subtracted from all
balances every minute.

Also. a time period is defined at contract creation time at which the
difference between held balances and the demurrage can be withdrawn to a
pre-selected address, which in turn can redistribute that token value.

In short: Everyone is taxed a little something every minute, and every
so often a decision is made on how to redistribute that tax.

## Features

- Continuous decay of all balances.

- Capture and redistribution of decayed balances.

- Per-minute decay resolution.

- Minting and burning of vouchers.

- Grant and revoke access to mint and burn vouchers.

- Voucher expiration (modifiable anytime after publishing).

- Supply cap (modifiable anytime after publishing).

- Constant gas usage across exponential calculations.

## Nomenclature

‘`Demurrage`’  
A percentage of token supply that will continuously be removed.

‘`Demurrage Period`’  
A period of time denominated in minutes after which demurraged amounts
are available for redistribution.

‘`Sink Account`’  
The intermediate beneficiary of the demurraged amount, which may or may
not redistribute value.

‘`Base balance`’  
The inflated balance of each used which is stored for bookkeeping.

# Use Case

The use-case inspiring this implementation is in the context of issuance
of a *voucher* representing a credit obligation of an *Issuer* or
*Association of Issuers*.

This voucher can be redeemed as payment for the products of the Issuer.

The Issuer is the entity legally obligated to redeem the voucher as
payment.

Introducing demurrage on this vehicle discourages *withholding* the
voucher, for example for speculative advantage.

This also encourages increased *velocity* of voucher use.

## Example

Given:

- 10 voucher holders.

- A total supply of 1000 tokens.

- Demurrage of 2% per 30 days (43200 minutes).

- Redistribution period of 30 days (43200 minutes).

If no trades are made, the resulting balances after one redistribution
period of every user would be 98 Vouchers.

The Sink Address will have a balance of 20 vouchers after the same
period.

Note that after the redistribution the total of all balances will equal
the total minted amount.

Note that all accounts holding such vouchers are effected by demurrage
(even the Sink Account, pending redistribution).

# Smart contract

## Common interfaces

The smart contract is written in solidity, compatible with 0.8.x.

It implements a number of interfaces both from the Ethereum (ERC)
standards aswell as the Community Inclusion Currency contract interface
suite.

### ERC standard interfaces

- [ERC20 - Token Standard](https://eips.ethereum.org/EIPS/eip-20)

- [ERC165 - Standard Interface
  Detection](https://eips.ethereum.org/EIPS/eip-165)

- [ERC173 - Contract Ownership
  Standard](https://eips.ethereum.org/EIPS/eip-173)

- [ERC5679 - Token Minting and Burning (as part of CIC.Minter and
  CIC.Burner)](https://eips.ethereum.org/EIPS/eip-5679)

### CIC interfaces

- [Burner](https://git.grassecon.net/cicnet/cic-contracts/src/branch/master/solidity/Burner.sol)

- [Expire](https://git.grassecon.net/cicnet/cic-contracts/src/branch/master/solidity/Expire.sol)

- [Minter](https://git.grassecon.net/cicnet/cic-contracts/src/branch/master/solidity/Minter.sol)

- [Seal](https://git.grassecon.net/cicnet/cic-contracts/src/branch/master/solidity/Seal.sol)

- [Writer](https://git.grassecon.net/cicnet/cic-contracts/src/branch/master/solidity/Writer.sol)

## Dependencies

The token contract uses the
[ADBKMath](https://github.com/abdk-consulting/abdk-libraries-solidity/blob/master/ABDKMath64x64.sol)
library to calculate exponentials.

## Permissions

The smart contract defines three levels of access.

1.  Voucher contract owner

2.  Voucher minter

3.  Voucher holder

### Contract owner

When the contract is published to the network, the signer account of the
publishing transaction will be the contract owner.

Contract ownership can be changed by the owner using the **ERC173**
standard interface.

### Minter

A minter has access to mint vouchers, and to burn vouchers from its own
balance.

Only the contract owner may mint, and may add and remove minters.
Minters may be added and removed using the **CIC Writer** interface, as
long as the `WRITER_STATE` seal is not set. See [Sealing the
contract](#seal_005fstate) for further details.

The contract owner is automatically a minter.

### Holder

Any address may hold vouchers, and transfer vouchers from their balance.

Minters and the contract owner are automatically token holders.

All token holders are subject to demurrage.

## Publishing the contract

The contract is published with the following arguments:

‘`name`’  
ERC20 voucher name

‘`symbol`’  
ERC20 voucher symbol

‘`decimals`’  
ERC20 decimal count

‘`decayLevel`’  
Level of decay per minute. See [Specifying
demurrage](#specifying_005fdemurrage) below for further details.

‘`periodMinutes`’  
Number of minutes between each time the demurraged value can be
withdrawn to the *Sink Account*. See [Withdrawing demurraged
value](#withdrawing) below for further details. The period may not be
altered.

‘`defaultSinkAddress`’  
The initial *Sink Address*. The address may be altered as long as the
`SINK_STATE` seal has not been set. See [Sealing the
contract](#seal_005fstate) for further details.

### Specifying demurrage

The *input parameter* to the contract is a 128-bit positive fixed-point
number, where the most significant 64 bits represent the integer part,
and the lower 64 bits represents the decimals part, each consecutive
lesser bit halving the value of the previous bit.

For example, The byte value `00000000 00000002 a0000000 00000000`,
representing a zero-stripped binary value of $10.101$. This translates
to the (base 10) decimal value $2.625$. The decimal part is calculated
as, from left to right: $(1 * 0.5) + (0 * 0.25) + (1 * 0.125)$.

#### Calculating the demurrage parameter

The minute granularity of the demurrage value is calculating using the
continuous decay function.

For example, for a demurrage of 2% per 30 days (43200 minutes), the
input value will be:

$(1-0.02)^(1/43200) ~ 0.99999953234484737109$

The decimal part of the fixed-point representation of this value is:

`fffff8276fb8cfff`

The input parameter becomes:

`0000000000000000ffffa957014dc7ff`

See [Tools](#tools) for additional help generating the necessary values.

Note that attempting to publish a voucher contract with no (zero)
demurrage will fail (if demurrage is not needed, use another contract).

## Using the contract

### Withdrawing demurrage

After each redistribution period, the demurraged value of that period
can be withdrawn to the currently defined *Sink Account*.

The demurrage is calculated as from the total supply of voucher at the
end of the period.

Withdrawal should happen implicitly duing normal operation of the
contract. See [Side-effects in state changes](#sideeffects).

To explicitly credit the *Sink Address* with the demurrage value after a
period has been exceeded, the `changePeriod()` (`8f1df6bc`) method can
be called.

### Setting voucher expiry

The effect of a voucher expiring is that all balances will be frozen,
and all state changes affecting token balances will be blocked.

Expiry is defined in terms of redistribution periods. For example, if
the redistribution period is 30 days, and the expity is 3, then the
voucher expires after 90 days.

The expiry takes effect immediately when the redistribution period time
has been exceeded.

When the contract is published, no expiry is set.

Expiry may be set after publishing using the `CIC.Expire` interface.

If the `EXPIRE_STATE` seal has been set, expiry may not be changed
further.

### Capping voucher supply

The effect of a voucher supply cap is that all `CIC.Minter` calls will
fail if the total supply after minting exceeds the defined supply cap.

The supply cap still allows vouchers to be minted after `CIC.Burn`
calls, provided that the previous condition holds.

To apply the supply cap, the method `setMaxSupply(uint256) (6f8b44b0)`
is used.

### Side-effects in state changes

All state changes involving voucher values implicitly execute two core
methods to ensure application of the demurrage and redistribution.

The two methods are:

`applyDemurrage() (731f237c)`  
Calculates the demurrage modifier of all balances according to the
current timestamp.

`changePeriod() (8f1df6bc)`  
If the previously executed period change does not match the current
period, the period is changed, and the *Sink Address* is credited with
the demurrage amount of the current total supply.

Both of these methods are *noop* if no demurrage or withdrawal is
pending, respectively.

Examples of state changes that execute these methods include
`ERC20.transfer(...)`, `ERC20.transferFrom(...)` and `CIC.mintTo(...)`.

### Sealing the contract

Certain mutable core parameters of the contract can be *sealed*, meaning
prevented from being modifier further.

Sealing is executed using the `CIC.Seal` interface.

The sealing of parameters is irreversible.

The sealable parameters are[^1]:

`WRITER_STATE`  
The `CIC.Writer` interface is blocked. The effect of this is that no
more changes may be made to which accounts have minter permission.

`SINK_STATE`  
After setting this seal, the *Sink Address* may not be changed.

`EXPIRY_STATE`  
Prevents future changes to the voucher expiry date[^2].

`CAP_STATE`  
Immediately prevents future voucher minting, regardless of permissions.

## Gas usage

Gas usage is constant regardless of the amount of time passed between
each execution of demurrage and redistribution period calculations.

## Caveats

A `ERC20.transferFrom(...)` following an `ERC20.approve(...)` call, when
called across period thresholds, may fail if margin to demurraged amount
is insufficient.

# Tools

When installed as a python package, `erc20-demurrage-token` installs the
`erc20-demurrage-token-publish` executable script, which can be used to
publish smart contract instances.

While the man page for the tool can be referred to for general
information of the tool usage, two argument flags warrant special
mention in the context of this documentation.

`--demurrage-level`  
The percentage of demurrage in terms of the redistribution period,
defined as parts-per-million.

`--redistribution-period`  
A numeric value denominated in *minutes* to define the redistribution
period of the voucher demurrage.

For example, to define a 2% demurrage value for a redistribution period
of 30 days (43200 minutes), the argument to the argument flags would be:

    erc20-demurrage-token-publish --demurrage-level 20000 --redistribution-period 43200 ...

## Calculating fixed-point values

The `erc20-demurrage-token` package installs the python package `dexif`
as part of its dependencies.

This package in turn provides an epinymous command-line tool (`dexif`)
which converts decimal values to a 128-bit fixed-point value expected by
the contract constructor.

An example:

    $ dexif 123.456
    7b74bc6a7ef9db23ff

    $ dexif -x 7b74bc6a7ef9db23ff
    123.456

## Contract interaction with chainlib-eth

All smart contract tests are implementing using
[chainlib-eth](https://git.defalsify.org/chainlib-eth) from the
chaintool suite.

The `eth-encode` tool from the `chainlib-eth` python package may be a
convenient way to interact with contract features.

Some examples include:

    # explicitly call changePeriod()
    $ eth-encode --mode tx --signature changePeriod -e <contract_address> -y <key_file> ...

    # Set the sink address seal (The integer value of the SINK_STATE flag is 2 at the time of writing)
    $ eth-encode --mode tx --signature seal  -e <contract_address> -y <key_file> ... u:2

    # Query current sink address of contract
    $ eth-encode --mode call --signature sinkAddress -e <contract_address> ...

[^1]: Please refer to the contract source code for the numeric values of
    the state flags

[^2]: The `EXPIRY_STATE` is implicitly set after expiration.
