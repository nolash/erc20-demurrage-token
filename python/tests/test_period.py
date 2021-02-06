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

#BLOCKTIME = 5 # seconds
TAX_LEVEL = 10000 * 2 # 2%
#PERIOD = int(60/BLOCKTIME) * 60 * 24 * 30 # month
PERIOD = 1


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

        c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL * (10 ** 32), PERIOD, self.sink_address).transact({'from': self.w3.eth.accounts[0]})

        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

        self.start_block = self.w3.eth.blockNumber
        b = self.w3.eth.getBlock(self.start_block)
        self.start_time = b['timestamp']


    def tearDown(self):
        pass


    def test_period(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        self.eth_tester.time_travel(self.start_time + 61)
        tx_hash = self.contract.functions.changePeriod().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        redistribution = self.contract.functions.redistributions(1).call()
        self.assertEqual(2, self.contract.functions.toRedistributionPeriod(redistribution).call())
        self.assertEqual(2, self.contract.functions.actualPeriod().call())


if __name__ == '__main__':
    unittest.main()
