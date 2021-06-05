SOLC = /usr/bin/solc

all: multi single

multi_nocap:
	$(SOLC) DemurrageTokenMultiNocap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiNocap.json
	$(SOLC) DemurrageTokenMultiNocap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiNocap.bin
	truncate -s -1 DemurrageTokenMultiNocap.bin

multi_cap:
	$(SOLC) DemurrageTokenMultiCap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiCap.json
	$(SOLC) DemurrageTokenMultiCap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiCap.bin
	truncate -s -1 DemurrageTokenMultiCap.bin

multi: multi_nocap multi_cap

single_nocap:
	$(SOLC) DemurrageTokenSingleNocap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenSingleNocap.json
	$(SOLC) DemurrageTokenSingleNocap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenSingleNocap.bin
	truncate -s -1 DemurrageTokenSingleNocap.bin

single_cap:
	$(SOLC) DemurrageTokenSingleCap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenSingleCap.json
	$(SOLC) DemurrageTokenSingleCap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenSingleCap.bin
	truncate -s -1 DemurrageTokenSingleCap.bin

single: single_nocap single_cap

test: all
	python ../python/tests/test_basic.py
	python ../python/tests/test_period.py
	python ../python/tests/test_redistribution.py
	python ../python/tests/test_pure.py

install: all
	cp -v DemurrageToken*.{json,bin} ../python/erc20_demurrage_token/data/
	
.PHONY: test install
