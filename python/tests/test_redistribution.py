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
        self.sink_address = self.w3.eth.accounts[9]

        c = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        tx_hash = c.constructor('Foo Token', 'FOO', 6, TAX_LEVEL, PERIOD, self.sink_address).transact({'from': self.w3.eth.accounts[0]})

        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.contract = self.w3.eth.contract(abi=self.abi, address=r.contractAddress)

        self.start_block = self.w3.eth.blockNumber
        logg.debug('starting at block number {}'.format(self.start_block))

    def tearDown(self):
        pass


    def debug_periods(self):
        pactual = self.contract.functions.actualPeriod().call()
        pstart = self.contract.functions.periodStart().call()
        pduration = self.contract.functions.periodDuration().call()
        blocknumber = self.w3.eth.blockNumber;
        logg.debug('actual {} start {} duration {} blocknumber {}'.format(pactual, pstart, pduration, blocknumber))


    # TODO: check receipt log outputs
    @unittest.skip('foo')
    def test_redistribution_storage(self):
        self.contract.functions.mintTo(self.w3.eth.accounts[1], 2000).transact()

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[2], 500).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('tx before {}'.format(r))
        self.assertEqual(r.status, 1)

        self.eth_tester.mine_blocks(PERIOD)

        redistribution = self.contract.functions.redistributions(0).call();
        self.assertEqual(redistribution.hex(), '000000000100000000000000000000000000000000000007d000000000000001')

        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[0], 1000000).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        redistribution = self.contract.functions.redistributions(1).call()
        self.assertEqual(redistribution.hex(), '000000000000000000000000000000000000000000000f4a1000000000000002')
    

    def test_redistribution_balance_on_zero_participants(self):
        supply = 1000000000000
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], supply).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)

        self.eth_tester.mine_blocks(PERIOD)

        tx_hash = self.contract.functions.applyTax().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('r {}'.format(r))
        self.assertEqual(r.status, 1)

        redistribution = self.contract.functions.redistributions(0).call();
        supply = self.contract.functions.totalSupply().call()

        sink_increment = int(supply * (TAX_LEVEL / 1000000))
        for l in r['logs']:
            if l.topics[0].hex() == '0x337db9c77a0769d770641c73e3282be23b15e2bddd830c219461dec832313389': # event Taxed(uint256,uint256)
                period = int.from_bytes(l.topics[1], 'big')
                self.assertEqual(period, 1)
                b = bytes.fromhex(l.data[2:])
                remainder = int.from_bytes(b, 'big')
                self.assertEqual(remainder, sink_increment)
                logg.debug('period {} remainder {}'.format(period, remainder))

        sink_balance = self.contract.functions.balanceOf(self.sink_address).call()
        logg.debug('{} {}'.format(sink_increment, sink_balance))
        self.assertEqual(sink_balance, int(sink_increment * 0.98))
        self.assertEqual(sink_balance, int(sink_increment * (1000000 - TAX_LEVEL) / 1000000))

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, supply - sink_increment)


    @unittest.skip('foo')
    def test_redistribution_balance_to_single(self):
        z = 0
        for i in range(3):
            redistribution = self.contract.functions.redistributions(0).call();
            logg.debug('foo {}'.format(redistribution.hex()))
            self.debug_periods();

            self.contract.functions.mintTo(self.w3.eth.accounts[i], 1000000*(i+1)).transact()
            z += 1000000*(i+1)

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[3], 1000000).transact({'from': self.w3.eth.accounts[0]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('tx before r {}'.format(r))

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[0]).call()
        self.assertEqual(balance, 0)

        self.eth_tester.mine_blocks(PERIOD)

        redistribution = self.contract.functions.redistributions(0).call();
        self.assertEqual(redistribution.hex(), '000000000100000000000000000000000000000000005b8d8000000000000001')

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[3], 0).transact({'from': self.w3.eth.accounts[0]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('tx after r {}'.format(r))

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[0]).call()
        self.assertEqual(balance, int(z * 0.02 * 0.98))

        redistribution = self.contract.functions.redistributions(1).call();
        self.assertEqual(redistribution.hex(), '000000000000000000000000000000000000000000005b8d8000000000000002')


    #@unittest.expectedFailure
    @unittest.skip('foo')
    def test_redistribution_balance_to_two(self):
        z = 0
        for i in range(5):
            redistribution = self.contract.functions.redistributions(0).call();
            logg.debug('foo {}'.format(redistribution.hex()))
            self.debug_periods();

            self.contract.functions.mintTo(self.w3.eth.accounts[i], 1000000*(i+1)).transact()
            z += 1000000*(i+1)

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[5], 1000000).transact({'from': self.w3.eth.accounts[0]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[6], 2000000).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[0]).call()
        self.assertEqual(balance, 0)

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, 0)

        self.eth_tester.mine_blocks(PERIOD) 
        self.debug_periods();

        redistribution = self.contract.functions.redistributions(0).call();
        self.assertEqual(redistribution.hex(), '00000000020000000000000000000000000000000000e4e1c000000000000001')

        tx_hash = self.contract.functions.transfer(self.w3.eth.accounts[3], 0).transact({'from': self.w3.eth.accounts[0]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[0]).call()
        #self.assertEqual(balance, 117600)
        self.assertEqual(balance, int((z * 0.02 * 0.98) / 2))

        redistribution = self.contract.functions.redistributions(1).call();
        self.assertEqual(redistribution.hex(), '00000000000000000000000000000000000000000000e4e1c000000000000002')


if __name__ == '__main__':
    unittest.main()

 
