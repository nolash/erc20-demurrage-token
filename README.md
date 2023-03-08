# RedistributedDemurrageToken

## Use Case
* Vouchers
  * A Publisher may publish a RedistributedDemurrageToken (Voucher) representing a credit obligation of an Issuer or Association of Issuers that can be redeemed as payment for the products of the Issuer. The Issuer is the entity legally obligated to redeem the voucher as payment.
  * Decay: The Publisher can specify an decay rate such as 2% as well as a redistribution period. After the redistribution period such as a month. Assuming an account holder has not had any transfers they will have a new balance of their original balance*2%. Note that the numeric decay will happen continuously by the minute.
  * Redistribution: The missing (demurraged) balances will be added to the balance of the SINK address. So once a redistribution period (e.g. once a month) the total supply of all holders including the SINK will return to the minted supply.
  * This is meant to result as a disincentivization to hold (hodl) the Voucher without causing price inflation, as the total supply is stable.
  * Example 
    -  With a demurrage of 2% (and redistribution period of 1 month) - If there are 10 users all with balances of 100 Vouchers (and only 2 of them trade that month (assume they trade back and forth with no net balance change)). 
    - Then the resulting balances after one redistribution period of ALL users (regardless of their trading) would be 98 Vouchers and 20 Voucher would be the balance of the SINK address. Assuming the SINK address is redistributed (as a Community Fund) back to users, it’s balance would again reach 20 the next redistribution period. 
    - Note that after the redistribution the total of all balances will equal the total minted amount. 
    - Note that all accounts holding such Vouchers are effected by demurrage.

## Nomenclature

* `Demurrage` aka Decay amount: A percentage of token supply that will gradually be removed over a redstribution period and then redistributed to the SINK account.
* Base balance: The inflated balance of each user is stored for bookkeeping.
* Sink Token Address: Rounding errors and if no one trades the tax goes to this address
* Demurrage Period (minutes)- aka `period`: The number of minutes over which a user must be _active_ to receive tax-redistibution. 


## Ownership

* Contract creator is owner
* Ownership can be transferred


## Mint

* Minters are called writers. Contract owner can add and remove writers.
* A writer can remove itself
* The interface says the amount and is at the caller's discretion per contract call. _validation_ is outside of this contract.
* Writers can mint any amount. If supply cap is set, minting will be limited to this cap.


## Input parameters

The redistrbution period is passed to the contract in minutes. E.g. a redistribution period of one month would be approximately 43200 minutes.

The demurrage level specified as the percentage of continuous growth per minute:

`(1 - percentage) ^ (1 / period)`

E.g. A demurrage of 2% monthly would be defined as:

`(1 - 0.02) ^ (1 / 43200) ~ 0.99999953234484737109`

The number must be provided to the contract as a 64x64 bit fixed-point number (where the integer part is 0).

A script is included in the python package to publish the contract which takes the input as a percentage as parts-per-million and converts the correct input argument for the contract. The calculation can be found in the function `process_config_local` in `python/erc20_demurrage_token/runnable/publish.py`. It uses the python module [dexif](https://pypi.org/project/dexif/) to perform the fixed-point conversion.


## Demurrage calculation

The demurrage calculation inside the contract is done by the following formula, where `demurrageLevel` is the demurrage level input parameter of the contract:

`newDemurrageModifier = currentDemurrageModifier * (e ^ (ln(demurrageLevel) * minutes))`

Holding Tax (`demurrage`) is applied when a **mint** or **transfer**; (it can also be triggered explicitly)
- Note that the token supply _stays the same_ but a virtual _balance output_ is created.
- Updates `demurrageModifier` which represents the accumulated tax value and is an exponential decay step (of size `demurrage`) for each minute that has passed.


All client-facing values (_balance output_ , _transfer inputs_) are adjusted with `demurrageModifier`.

e.g. `_balance output_ = user_balance - user_balance * demurrageModifier`


## Redistribution

* One redistribution entry is added to storage for each `period`;
* When `mint` is triggered, the new totalsupply is stored to the entry
* When `transfer` is triggered, and the account did not yet participate in the `period`, the entry's participant count is incremented. 
* Redistributed tokens are added to the balance of the _sink address_ given when the contract is published.
* _sink address_ may be changed.


## Data representation

Token parameters are truncated when calculating demurrage and redistribution:

* Redistribution period: 32 bits
* Token supply: 72 bits
* Demurrage modifier: 64 bits


## Expiration

A token may set to expire at a certain point in time. After the expiry, no more transfers may be executed. From that point on, balances are frozen and demurrage is halted.

Expiration may be set in terms of redistribution periods.

Unless sealed (see below), expiration may be changed at any time to any future redistribution period. However, once expired, expiration may not be changed further.


## Supply

Unless sealed (see below), Supply limit may be set and change at any time. Supply may never be directly set to less than the current supply. However, contract _writers_ may burn tokens in their possession using the `burn()` method, which will effectively reduce the supply.


## Mutability

The following parameters may not be changed after contract is published:

* Demurrage level
* Redistribution period

The contract provides a sealing feature which prohibits further changes to parameters that can initially be edited. These include:

* Adding and removing writers (addresses that may mint tokens)
* Sink addres
* Expiry period
* Supply limit


## Gas usage

The token contract uses the [ADBKMath](https://github.com/abdk-consulting/abdk-libraries-solidity/blob/master/ABDKMath64x64.sol) library to calculate exponentials.

Gas usage is constant regardless of the amount of time passed between each execution of demurrage and redistribution period calculations.


## QA

* Tests are implemented using the `chaintool` python package suite.


## Known issues

* A `transferFrom` following an `approve` call, when called across period thresholds, may fail if margin to demurraged amount is insufficient.
