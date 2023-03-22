SOLC = /usr/bin/solc

all: single_nocap

single_nocap:
	$(SOLC) DemurrageTokenSingleNocap.sol --abi --evm-version byzantium | awk 'NR==4' > DemurrageTokenSingleNocap.json
	$(SOLC) DemurrageTokenSingleNocap.sol --bin --evm-version byzantium | awk 'NR==4' > DemurrageTokenSingleNocap.bin
	$(SOLC) DemurrageTokenSingleNocap.sol --metadata --evm-version byzantium | awk 'NR==4' > DemurrageTokenSingleNocap.metadata.json
	truncate -s -1 DemurrageTokenSingleNocap.bin

single: single_nocap

test: all
	python ../python/tests/test_basic.py
	python ../python/tests/test_period.py
	python ../python/tests/test_redistribution.py
	python ../python/tests/test_pure.py

install: all
	cp -v DemurrageToken*.json ../python/erc20_demurrage_token/data/
	cp -v DemurrageToken*.bin ../python/erc20_demurrage_token/data/
	
.PHONY: test install
