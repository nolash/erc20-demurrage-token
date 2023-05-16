all: python solidity doc
python:
	make -C python
solidity:
	make -C solidity
doc:
	make -C doc/texinfo
readme:
	make -C doc/texinfo readme
	pandoc -f docbook -t gfm doc/texinfo/build/docbook.xml > README.md


