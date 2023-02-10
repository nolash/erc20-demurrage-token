# standard imports
import os
import unittest
import json
import logging

# third-party imports
import web3
import eth_tester
import eth_abi

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('eth.vm').setLevel(logging.WARNING)

testdir = os.path.dirname(__file__)

TAX_LEVEL = 10000 * 2 # 2%


class Test(unittest.TestCase):

    contract = None

    def setUp(self):
        eth_params = eth_tester.backends.pyevm.main.get_default_genesis_params({
            'gas_limit': 9000000,
            })

        f = open(os.path.join(testdir, '../../solidity/RedistributedDemurrageToken.bin'), 'r')
        self.bytecode = f.read()
        f.close()

        f = open(os.path.join(testdir, '../../solidity/RedistributedDemurrageToken.json'), 'r')
        self.abi = json.load(f)
        f.close()

        backend = eth_tester.PyEVMBackend(eth_params)
        self.eth_tester =  eth_tester.EthereumTester(backend)
        provider = web3.Web3.EthereumTesterProvider(self.eth_tester)
        self.w3 = web3.Web3(provider)
        self.sink_address = self.w3.eth.accounts[9]

    def tearDown(self):
        pass


    def test_construct(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            print('construct: {}'.format(r['gasUsed']))


    def test_gas_changeperiod(self):
        period = 43200
        for i in range(5):
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            period_seconds = period * 60
            self.eth_tester.time_travel(start_time + period_seconds + (60 * (10 ** i)))
            tx_hash = contract.functions.changePeriod().transact()
            r = self.w3.eth.getTransactionReceipt(tx_hash)

            print('changePeriod {} ({}): {}'.format(i, 60 * (10 ** i), r['gasUsed']))


    def test_mint(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            tx_hash = contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            print ('mintTo: {}'.format(r['gasUsed']))


    def test_transfer(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact({'from': self.w3.eth.accounts[0]})

            tx_hash = contract.functions.transfer(self.w3.eth.accounts[2], 1000000).transact({'from': self.w3.eth.accounts[1]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            print ('transfer: {}'.format(r['gasUsed']))


    def test_approve(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact({'from': self.w3.eth.accounts[0]})

            tx_hash = contract.functions.approve(self.w3.eth.accounts[2], 1000000).transact({'from': self.w3.eth.accounts[1]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            print ('approve: {}'.format(r['gasUsed']))


    def test_transferfrom(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact({'from': self.w3.eth.accounts[0]})

            contract.functions.approve(self.w3.eth.accounts[2], 1000000).transact({'from': self.w3.eth.accounts[1]})

            tx_hash = contract.functions.transferFrom(self.w3.eth.accounts[1], self.w3.eth.accounts[3], 1000000).transact({'from': self.w3.eth.accounts[2]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            print ('transferFrom: {}'.format(r['gasUsed']))


    def test_redistribute_default(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            for i in range(100):
                addr = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
                contract.functions.mintTo(addr, 1000000 * (i+1)).transact({'from': self.w3.eth.accounts[0]})

            self.eth_tester.time_travel(start_time + period * 60 + 1)
            redistribution = contract.functions.redistributions(0).call()
            tx_hash = contract.functions.changePeriod().transact({'from': self.w3.eth.accounts[2]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            print ('chainPeriod -> defaultRedistribution: {}'.format(r['gasUsed']))


    def test_redistribution_account(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact({'from': self.w3.eth.accounts[0]})
            contract.functions.transfer(self.w3.eth.accounts[2], 1000000).transact({'from': self.w3.eth.accounts[1]})

            for i in range(100):
                addr = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
                contract.functions.mintTo(addr, 1000000 * (i+1)).transact({'from': self.w3.eth.accounts[0]})

            self.eth_tester.time_travel(start_time + period * 60 + 1)
            redistribution = contract.functions.redistributions(0).call()
            tx_hash = contract.functions.applyRedistributionOnAccount(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[2]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            self.assertEqual(r.logs[0].topics[0].hex(), '0x9a2a887706623ad3ff7fc85652deeceabe9fe1e00466c597972079ee91ea40d3')
            print ('redistribute account: {}'.format(r['gasUsed']))


    def test_redistribution_account_transfer(self):
            period = 10
            c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
            tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), period, self.sink_address).transact({'from': self.w3.eth.accounts[0]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

            start_block = self.w3.eth.blockNumber
            b = self.w3.eth.getBlock(start_block)
            start_time = b['timestamp']

            contract.functions.mintTo(self.w3.eth.accounts[1], 2000000).transact({'from': self.w3.eth.accounts[0]})
            contract.functions.transfer(self.w3.eth.accounts[2], 1000000).transact({'from': self.w3.eth.accounts[1]})

            for i in range(10):
                addr = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
                contract.functions.mintTo(addr, 1000000 * (i+1)).transact({'from': self.w3.eth.accounts[0]})

            self.eth_tester.time_travel(start_time + period * 60 + 1)
            redistribution = contract.functions.redistributions(0).call()
            contract.functions.changePeriod().transact({'from': self.w3.eth.accounts[0]})
            tx_hash = contract.functions.transfer(self.w3.eth.accounts[3], 100000).transact({'from': self.w3.eth.accounts[1]})
            r = self.w3.eth.getTransactionReceipt(tx_hash)
            self.assertEqual(r.logs[0].topics[0].hex(), '0x9a2a887706623ad3ff7fc85652deeceabe9fe1e00466c597972079ee91ea40d3')
            print ('redistribute account: {}'.format(r['gasUsed']))


if __name__ == '__main__':
    unittest.main()

 
