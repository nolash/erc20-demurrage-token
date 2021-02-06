# standard imports
import os
import unittest
import json
import logging
import math

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
TAX_LEVEL = int((10000 * 2) * (10 ** 32)) # 2%
PERIOD = 10


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
        tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL, PERIOD, self.sink_address).transact({'from': self.w3.eth.accounts[0]})

        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

        self.start_block = self.w3.eth.blockNumber


    def tearDown(self):
        pass


    def test_tax_period(self):
        t = self.contract.functions.taxLevel().call()
        logg.debug('taxlevel {}'.format(t))

        a = self.contract.functions.toTaxPeriodAmount(1000000, 0).call()
        self.assertEqual(a, 1000000)

        a = self.contract.functions.toTaxPeriodAmount(1000000, 1).call()
        self.assertEqual(a, 980000)

        a = self.contract.functions.toTaxPeriodAmount(1000000, 2).call()
        self.assertEqual(a, 960400)

        a = self.contract.functions.toTaxPeriodAmount(980000, 1).call()
        self.assertEqual(a, 960400)


    def test_fractional_state(self):
        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            self.contract.functions.remainder(2, 1).call();

        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            remainder = self.contract.functions.remainder(0, 100001).call();

        remainder = self.contract.functions.remainder(1, 2).call();
        self.assertEqual(remainder, 0);
   
        whole = 5000001
        parts = 20000
        expect = whole - (math.floor(whole/parts) * parts) 
        remainder = self.contract.functions.remainder(parts, whole).call();
        self.assertEqual(remainder, expect)

        parts = 30000
        expect = whole - (math.floor(whole/parts) * parts) 
        remainder = self.contract.functions.remainder(parts, whole).call();
        self.assertEqual(remainder, expect)

        parts = 40001
        expect = whole - (math.floor(whole/parts) * parts) 
        remainder = self.contract.functions.remainder(parts, whole).call();
        self.assertEqual(remainder, expect)

if __name__ == '__main__':
    unittest.main()
