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
        c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL, PERIOD).transact({'from': self.w3.eth.accounts[0]})

        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

        self.start_block = self.w3.eth.blockNumber

    def tearDown(self):
        pass


    def test_hello(self):
        self.assertEqual(self.contract.functions.actualPeriod().call(), 1)
        self.eth_tester.mine_blocks(PERIOD)
        self.assertEqual(self.contract.functions.actualPeriod().call(), 2)


    def test_mint(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, 1024)

        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 976).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, 2000)


    def test_transfer(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)
        logg.debug('tx {}'.format(r))

        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance_alice, 524)

        balance_bob = self.contract.functions.balanceOf(self.w3.eth.accounts[2]).call()
        self.assertEqual(balance_bob, 500)

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)
        logg.debug('tx {}'.format(r))


    def test_transfer_from(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1024).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        tx_hash = self.contract.functions.approve(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)
        logg.debug('tx {}'.format(r))

        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance_alice, 1024)

        tx_hash = self.contract.functions.transferFrom(self.w3.eth.accounts[1], self.w3.eth.accounts[3], 500).transact({'from': self.w3.eth.accounts[2]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)
        logg.debug('tx {}'.format(r))

        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance_alice, 524)

        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[3]).call()
        self.assertEqual(balance_alice, 500)


    def test_apply_tax(self):
        self.eth_tester.mine_blocks(PERIOD)
        tx_hash = self.contract.functions.applyTax().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(self.contract.functions.redistributionCount().call(), 2)
        self.assertEqual(self.contract.functions.demurrageModifier().call(), 980000)

        self.eth_tester.mine_blocks(PERIOD)
        tx_hash = self.contract.functions.applyTax().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(self.contract.functions.redistributionCount().call(), 3)
        self.assertEqual(self.contract.functions.demurrageModifier().call(), 960400)


    def test_tax_balance(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1000).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        self.eth_tester.mine_blocks(PERIOD)
        tx_hash = self.contract.functions.applyTax().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, 980)

    
    def test_taxed_transfer(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        self.eth_tester.mine_blocks(PERIOD)
        tx_hash = self.contract.functions.applyTax().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance_alice, 980000)

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[2], 500000).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('r {}'.format(r))
        self.assertEqual(r.status, 1)

        balance_alice = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        balance_alice_trunc = int(balance_alice/1000)*1000
        self.assertEqual(balance_alice_trunc, 480000)

        balance_bob = self.contract.functions.balanceOf(self.w3.eth.accounts[2]).call()
        balance_bob_trunc = int(balance_bob/1000)*1000
        self.assertEqual(balance_bob_trunc, 500000)


if __name__ == '__main__':
    unittest.main()
