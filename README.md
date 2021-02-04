# RedistributedDemurrageToken

## Use Case
* Network / Basic Income Token
  * 100 Sarafu is distributed to anyone in Kenya after user validation by the owner of a faucet which mints new Sarafu.
  * Validated users are those that validate their phone number in Kenya.
  * A monthly Sarafu holding tax (demurrage) of 2% is deducted from users 
  * Each month (after a number of blocks) the total amount tax is distributed evenly out to _active_ users.
    *  any single transaction by a user is considered _active_ (heartbeat) (possibly add minimum size of heartbeat in constructor (TODO))
  * This is meant to result in a disincentivization to hold (hodl) the Sarafu token and increase its usage as a medium of excahnge rather than a store of value.


## Variables

* Inputs to Constructor (Set only once during contract deployment can't be changed )  
  * `Demmurage` aka Decay amount: A percentage of token supply that will be charged once per - aka `period` and evenly redistributed to _active_ users 
  * Demmurage Period (blocks)- aka `period`: The number of blocks (equivalent to a time frame) over which a new Holding Fee is applied and redistributed. 
  * Inflated Balance: The inflated balance of each user is stored for bookkeeping.
  * Number of Decimals: Resolution on token (TODO) (Default 6)
  * Minimum Activity Volume: (TODO) the minimum transaction amount to be considered active
  * Sink Token Address: Rounding errors and if no one trades the tax goes to this address


## Ownership

* Contract creator is owner
* Ownership can be transferred (also to ownership void contract "no more changes can be made")


## Mint

* Owner can add minters
  - A faucet contract would be a minter and choose the amount of tokens to mint and distribute to new _validated_ users.
  - The interface says the amount and is at the caller's discretion per contract call. _validation_ is outside of this contract.
* Minters can mint any amount


## Demurrage
* Holding Tax (`demurrage`) is applied when a **mint** or **transfer** is triggered for first time/block in a new `period`; (it can also be triggered explicitly)
  - Supply _stays the same_.
  - Updates `demurrageModifier` which represents the accumulated tax value and is an exponential decay step (of size `demurrage`) for each `period`
    - `demurrageModifier = (1-demurrage)^period` 
      - e.g. a `demurrage` of 2% at a `period` of 0 would be give a `demurrageModifier= (1-0.02)^0 = 1-1 = 0`.
      - e.g. a `demurrage` of 2% at a `period` of 1 would be give a `demurrageModifier = (1-0.02)^1 = 0.98`.
      - e.g. a `demurrage` of 2% at a `period` of 2 would be give a `demurrageModifier = (1-0.02)^2 = 0.9604`.
* All client-facing values (_balance output_ , _transfer inputs_) are adjusted with `demurrageModifier`.
  - e.g. `_balance output_ = user_balance - user_balance * demurrageModifier`
* Edge case: `approve` call, which may be called on either side of a period.


## Redistribution

* One redistribution entry is added to storage for each period;
  - When `mint` is triggered, the new totalsupply is stored to the entry
  - When `transfer` is triggered, and the account did not yet participate in the `period`, the entry's participant count is incremented. 
* Account must have "participated" in a period to be redistribution beneficiary.
* Redistribution is applied when an account triggers a **transfer** for the first time in a new period;
  - Check if user has participated in `period`. (_active_ user heartbeat)
  - Each _active_ user balance is increased by `(total supply at end of period * demurrageModifier ) / number_of_active_participants` via minting
  - Participation field is zeroed out for that user.
* Fractions must be rounded down (TODO)
  - Remainder is "dust" and should be sent to a dedicated "sink" token address (TODO)
  - If no one is _active_ all taxes go to the same sink address


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
