# RedistributedDemurrageToken

## Use Case
* Network / Basic Income Token
  * 100 Sarafu is distributed to anyone in Kenya after user validation by the owner of a faucet which mints new Sarafu.
  * Validated users are those that validate their phone number in Kenya
  * A monthly Sarafu holding tax (demmurrage) of 2% is recorded as a `demurrageModiifer`.
  * Supply and user actual balances stay the same but are displayed minus the `demurrageModiifer`.
  * Each month the total amount of demurage is distributed out to users _active_ and the `demurrageModiifer` for each user is reset to zero.
    *  a single transaction is considered _active_ (heartbeat).
  * This is meant to result in a disincentivization to hold (hodl) the Sarafu token and increase it's usage as a medium of excahnge rather than a store of value.


## Inputs to Constructor (Set only once during contract deployment)

* 'Decay amount' (ppm) and period (blocks) is set at deploy time.
  - Cannot be changed
  - aka a holding Fee: A percentage of a users balance that will be charged and eventually redistributed to active users
* Demmurage Period: The time frame over which a new Holding Fee is applied and redistributed.


## Ownership

* Contract creator is owner
* Ownership can be transferred (also to ownership void contract to make permissionless)


## Mint

* Owner can add minters
  - A faucet contract would be a minter and set the amount of tokens to mint and distribute to new (validated) users.
* Minters can mint any amount


## Demurrage
* Tax is applied when a **mint** or **transfer** is triggered for first time in new period;
  - Supply _stays the same_.
  - Updates `demurrageModiifer` which represents an exponential decay step (of size 'Decay amount' and is a a percentage of user balance)
    - `demurrageModifier`_(i) = 'Decay amount' x demurrageModifier_(i-1) x user balance
* All client-facing values (_balance output_ , _transfer inputs_) are adjusted with `demurrageModifier`.
* Edge case: `approve` call, which may be called on either side of a period.


## Redistribution

* One redistribution entry is added to storage for each period;
  - When `mint` is triggered, the new totalsupply is stored to the entry
  - When `transfer` is triggered, and the account did not yet participate in the period, the entry's participant count `demurrageModifier` is incremented. 
* Account must have "participated" in a period to be redistribution beneficiary.
* Redistribution is applied when an account triggers a **transfer** for the first time in a new period;
  - Check if have participated in period.
  - Balance is increased by `(total supply at end of period * demurrage modifier ) / number of participants`
  - Participation field is zeroed out.
* Fractions must be rounded down (TODO)
  - Remainder is "dust" and should be sent to a dedicated "sink" address (TODO)


## Data structures

* One word per account:
  - bits 000-159: value
  - bits 160-255: period
  - (we have more room here in case we want to cram something else in)
* One word per redistribution period:
  - bits 000-055: period
  - bits 056-215: supply
  - bits 216-253: participant count
  - bits     254: Set if invidiual redistribution amounts are fractions (TODO)
  - bits     255: Set if "dust" has been transferred to sink (TODO)


## QA

* Basic python tests in place
* How to determine and generate test vectors, and how to adapt them to scripts.
* Audit sources?
