# standard imports
import os
import unittest
import json
import logging
import datetime

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
TAX_LEVEL = int(10000 * 2) # 2%
# calc "1-(0.98)^(1/518400)" <- 518400 = 30 days of blocks
# 0.00000003897127107225
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


    def test_hello(self):
        self.assertEqual(self.contract.functions.actualPeriod().call(), 1)
        self.eth_tester.time_travel(self.start_time + 61)
        self.assertEqual(self.contract.functions.actualPeriod().call(), 2)



    def test_apply_demurrage(self):
        modifier = 10 * (10 ** 37)
        demurrage_modifier = self.contract.functions.demurrageModifier().call()
        demurrage_modifier &= (1 << 128) - 1
        self.assertEqual(modifier, demurrage_modifier)

        self.eth_tester.time_travel(self.start_time + 59)
        demurrage_modifier = self.contract.functions.demurrageModifier().call()
        demurrage_modifier &= (1 << 128) - 1
        self.assertEqual(modifier, demurrage_modifier)

        self.eth_tester.time_travel(self.start_time + 61)
        tx_hash = self.contract.functions.applyDemurrage().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)

        demurrage_modifier = self.contract.functions.demurrageModifier().call()
        demurrage_modifier &= (1 << 128) - 1
        self.assertEqual(int(98 * (10 ** 36)), demurrage_modifier)


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

        self.eth_tester.time_travel(self.start_time + 61)
        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, int(2000 * 0.98))


    def test_minter_control(self):
        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[2], 1024).transact({'from': self.w3.eth.accounts[1]})
           
        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[1]})

        tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[0]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[2]).transact({'from': self.w3.eth.accounts[1]})

        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[2], 1024).transact({'from': self.w3.eth.accounts[1]})

        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            tx_hash = self.contract.functions.addMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[2]})

        tx_hash = self.contract.functions.removeMinter(self.w3.eth.accounts[1]).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        with self.assertRaises(eth_tester.exceptions.TransactionFailed):
            tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[2], 1024).transact({'from': self.w3.eth.accounts[1]})

    def test_base_amount(self):
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], 1000).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        self.eth_tester.time_travel(self.start_time + 61)

        self.contract.functions.applyDemurrage().transact()
        demurrage_modifier = self.contract.functions.demurrageModifier().call()
        demurrage_amount = self.contract.functions.toDemurrageAmount(demurrage_modifier).call()
        logg.debug('d {} {}'.format(demurrage_modifier.to_bytes(32, 'big').hex(), demurrage_amount))

        a = self.contract.functions.toBaseAmount(1000).call();
        self.assertEqual(a, 1020)


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


if __name__ == '__main__':
    unittest.main()
