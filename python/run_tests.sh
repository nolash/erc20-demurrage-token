#!/bin/bash

set -x
set -e

export PYTHONPATH=.

#modes=(MultiNocap MultiCap SingleCap SingleNocap)
#modes=(SingleCap SingleNocap) # other contracts need to be updted
modes=(SingleNocap) # other contracts need to be updted
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_basic.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_growth.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_amounts.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_single.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_burn.py
done

#modes=(SingleCap) # other contracts need to be updted
modes=()
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_period.py
done

modes=(SingleNocap) # other contracts need to be updted
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_redistribution_unit.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_redistribution_single.py
done

#modes=(MultiCap SingleCap)
modes=()
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_cap.py
done

#modes=(MultiCap MultiNocap)
#for m in ${modes[@]}; do
#	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_remainder.py
#	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_redistribution.py
#done

set +e
set +x
