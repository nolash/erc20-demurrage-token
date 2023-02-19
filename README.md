# RedistributedDemurrageToken

# RedistributedDemurrageToken

**Last edit: Will Ruddick Feburary 19 2023**

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

* Owner can add minters and remove
  - A faucet contract would be a minter and choose the amount of tokens to mint and distribute to new _validated_ users.
  - The interface says the amount and is at the caller's discretion per contract call. _validation_ is outside of this contract.
* A minter can remove itself
* Minters can mint any amount


## Demurrage
* Holding Tax (`demurrage`) is applied when a **mint** or **transfer**; (it can also be triggered explicitly)
  - Note that the token supply _stays the same_ but a virtual _balance output_ is created.
  - Updates `demurrageModifier` which represents the accumulated tax value and is an exponential decay step (of size `demurrage`) for each minute that has passed.
    - `demurrageModifier = (1-demurrage)^(minute_passed)` 
      - e.g. a `demurrage` of 2% after the 1st minute would be give a `demurrageModifier = (1-0.02)^1 = 0.98`.
      - e.g. a `demurrage` after the 2nd minute would be give a `demurrageModifier = (1-0.02)^2 = 0.9604`.
* All client-facing values (_balance output_ , _transfer inputs_) are adjusted with `demurrageModifier`.
  - e.g. `_balance output_ = user_balance - user_balance * demurrageModifier`


## Redistribution

* One redistribution entry is added to storage for each `period`;
  - When `mint` is triggered, the new totalsupply is stored to the entry
  - When `transfer` is triggered, and the account did not yet participate in the `period`, the entry's participant count is incremented. 
* Account must have "participated" in a period to be redistribution beneficiary.
* Redistribution is applied when an account triggers a **transfer** for the first time in a new `period`;
  - Check if user has participated in `period`. (_active_ user heartbeat)
  - Each _active_ user balance in the `period` is increased by `(total supply at end of period * demurrageModifier ) / number_of_active_participants` via minting
  - Participation field is zeroed out for that user.
* Fractions must be rounded down
  - Remainder is "dust" and should be sent to a dedicated Sink Token Address.
  - If no one is _active_ all taxes go to the Sink Token Address.


## Data structures

* One word per `account`:
  - bits 000-071: value
  - bits 072-103: period
  - bits 104-255: (Unused)
* One word per `redistributions` period:
  - bits 000-031: period
  - bits 032-103: supply
  - bits 104-139: participant count
  - bits 140-159: demurrage modifier
  - bits 160-254: (Unused)
  - bits     255: Set if individual redistribution amounts are fractions

### Notes

Accumulated demurrage modifier in `demurrageModifier` is 128 bit, but will be _truncated_ do 20 bits in `redistributions`. The 128 bit resolution is to used to reduce the impact of fractional drift of the long-term accumulation of the demurrage modifier. However, the demurrage snapshot values used in `redistributions` are parts-per-million and can be fully contained within a 20-bit value.


## QA

* Basic python tests in place
* How to determine and generate sufficient test vectors, and how to adapt them to scripts.
* Audit sources?

## Known issues

* A `transferFrom` following an `approve` call, when called across period thresholds, may fail if margin to demurraged amount is insufficient.
