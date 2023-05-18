all: pypi man

pypi:
	python setup.py sdist

man:
	mkdir -vp man/build
	chainlib-man.py -b 0x3fafff -d man/build -n erc20-demurrage-token-publish -v man
