SOLC = /usr/bin/solc

all:
	$(SOLC) DemurrageTokenMultiNocap.sol --abi --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiNocap.json
	$(SOLC) DemurrageTokenMultiNocap.sol --bin --evm-version byzantium | awk 'NR>3' > DemurrageTokenMultiNocap.bin
	truncate -s -1 DemurrageTokenMultiNocap.bin

test: all
	python ../python/tests/test_basic.py
	python ../python/tests/test_period.py
	python ../python/tests/test_redistribution.py

install: all
	cp -v DemurrageTokenMultiNocap.{json,bin} ../python/sarafu_token/data/
	
.PHONY: test install
