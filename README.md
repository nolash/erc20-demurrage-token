# RedistributedDemurrageToken

## Ownership

* Contract creator is owner
* Ownership can be transferred (also to ownership void contract)


## Mint

* Owner can add minters
  - A faucet contract would be a minter
* Minters can mint any amount


## Demurrage

* Decay amount (ppm) and period (blocks) is set at deploy time.
  - Cannot be changed
* Tax is applied when a **mint** or **transfer** is triggered for first time in new period;
  - Supply _stays the same_.
  - Updates `demurrageModiifer` which represents an exponential decay step.
* All client-facing values (_balance output_ , _transfer inputs_) are adjusted with `demurrageModifier`.
* Edge case: `approve` call, which may be called on either side of a period.


## Redistribution

* One redistribution entry is added to storage for each period;
  - When `mint` is triggered, the new totalsupply is stored to the entry
  - When `transfer` is triggered, and the account did not yet participate in the period, the entry's participant count is incremented.
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
