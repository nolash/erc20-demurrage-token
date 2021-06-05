#!/bin/bash

set -e

export PYTHONPATH=.

modes=(MultiNocap MultiCap SingleCap SingleNocap)
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_pure.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_period.py
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_basic.py
done

modes=(MultiCap SingleCap)
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_cap.py
done

modes=(SingleCap SingleNocap)
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_single.py
done

modes=(MultiCap MultiNocap)
for m in ${modes[@]}; do
	ERC20_DEMURRAGE_TOKEN_TEST_MODE=$m python tests/test_redistribution.py
done

set +e
