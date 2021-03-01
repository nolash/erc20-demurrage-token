SOLC = /usr/bin/solc

all:
	$(SOLC) RedistributedDemurrageToken.sol --abi --evm-version byzantium | awk 'NR>3' > RedistributedDemurrageToken.json
	$(SOLC) RedistributedDemurrageToken.sol --bin --evm-version byzantium | awk 'NR>3' > RedistributedDemurrageToken.bin
	truncate -s -1 RedistributedDemurrageToken.bin

test: all
	python ../python/tests/test_basic.py
	python ../python/tests/test_period.py
	python ../python/tests/test_redistribution.py

install: all
	cp -v RedistributedDemurrageToken.{json,bin} ../python/sarafu_token/data/
	
.PHONY: test install
