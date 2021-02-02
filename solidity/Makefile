SOLC = /usr/bin/solc

all:
	$(SOLC) RedistributedDemurrageToken.sol --abi --evm-version byzantium | awk 'NR>3' > RedistributedDemurrageToken.json
	$(SOLC) RedistributedDemurrageToken.sol --bin --evm-version byzantium | awk 'NR>3' > RedistributedDemurrageToken.bin
	truncate -s -1 RedistributedDemurrageToken.bin

test: all
	python ../python/tests/test_basic.py

install: all
	cp -v RedistributedDemurrageToken.{json,bin} ../python/eth_address_declarator/data/
	
.PHONY: test install
