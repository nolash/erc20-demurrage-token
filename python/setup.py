from setuptools import setup
import os

requirements = []
f = open('requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    requirements.append(l.rstrip())
f.close()

test_requirements = []
f = open('test_requirements.txt', 'r')
while True:
    l = f.readline()
    if l == '':
        break
    test_requirements.append(l.rstrip())
f.close()


man_dir = 'man/build'
setup(
        package_data={
            '': [
                'data/MintableFactor.bin',
                ],
            },
        include_package_data=True,
        install_requires=requirements,
        tests_require=test_requirements,
        data_files=[("man/man1", [
                os.path.join(man_dir, 'erc20-demurrage-token-publish.1'),
            ]
             )],
        )
