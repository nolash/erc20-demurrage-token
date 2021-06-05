SOLC = /usr/bin/solc

all: multi_nocap multi_cap single_nocap


multi_nocap:
	$(SOLC) DemurrageTokenMultiNocap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiNocap.json
	$(SOLC) DemurrageTokenMultiNocap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiNocap.bin
	truncate -s -1 DemurrageTokenMultiCap.bin

multi_cap:
	$(SOLC) DemurrageTokenMultiCap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiCap.json
	$(SOLC) DemurrageTokenMultiCap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiCap.bin
	truncate -s -1 DemurrageTokenMultiNocap.bin

multi: multi_nocap multi_cap

single_nocap:
	$(SOLC) DemurrageTokenSingleNocap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenSingleNocap.json
	$(SOLC) DemurrageTokenSingleNocap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenSingleNocap.bin
	truncate -s -1 DemurrageTokenSingleNocap.bin

test: all
	python ../python/tests/test_basic.py
	python ../python/tests/test_period.py
	python ../python/tests/test_redistribution.py
	python ../python/tests/test_pure.py

install: all
	cp -v DemurrageToken*.{json,bin} ../python/erc20_demurrage_token/data/
	
.PHONY: test install
