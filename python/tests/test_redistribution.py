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


    def debug_periods(self):
        pactual = self.contract.functions.actualPeriod().call()
        pstart = self.contract.functions.periodStart().call()
        pduration = self.contract.functions.periodDuration().call()
        blocknumber = self.w3.eth.blockNumber;
        logg.debug('actual {} start {} duration {} blocknumber {}'.format(pactual, pstart, pduration, blocknumber))


    # TODO: check receipt log outputs
    def test_redistribution_storage(self):
        self.contract.functions.mintTo(self.w3.eth.accounts[1], 1000000).transact()
        self.contract.functions.mintTo(self.w3.eth.accounts[2], 1000000).transact()

        external_address = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
        tx_hash = self.contract.functions.transfer(external_address, 1000000).transact({'from': self.w3.eth.accounts[2]})
        tx_hash = self.contract.functions.transfer(external_address, 999999).transact({'from': self.w3.eth.accounts[1]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('tx before {}'.format(r))
        self.assertEqual(r.status, 1)

        self.eth_tester.time_travel(self.start_time + 61)

        redistribution = self.contract.functions.redistributions(0).call();
        self.assertEqual(redistribution.hex(), '000000000100000000000000000000000000000000001e848000000000000001')

        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[0], 1000000).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(r.status, 1)

        redistribution = self.contract.functions.redistributions(1).call()
        self.assertEqual(redistribution.hex(), '000000000000000000000000000000000000000000002dc6c000000000000002')
    

    def test_redistribution_balance_on_zero_participants(self):
        supply = 1000000000000
        tx_hash = self.contract.functions.mintTo(self.w3.eth.accounts[1], supply).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)

        self.eth_tester.time_travel(self.start_time + 61)

        tx_hash = self.contract.functions.applyDemurrage().transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('r {}'.format(r))
        self.assertEqual(r.status, 1)
        tx_hash = self.contract.functions.changePeriod().transact()
        rr = self.w3.eth.getTransactionReceipt(tx_hash)
        self.assertEqual(rr.status, 1)

        redistribution = self.contract.functions.redistributions(0).call();
        supply = self.contract.functions.totalSupply().call()

        sink_increment = int(supply * (TAX_LEVEL / 1000000))
        for l in r['logs']:
            if l.topics[0].hex() == '0xa0717e54e02bd9829db5e6e998aec0ae9de796b8d150a3cc46a92ab869697755': # event Decayed(uint256,uint256,uint256,uint256)
                period = int.from_bytes(l.topics[1], 'big')
                self.assertEqual(period, 2)
                b = bytes.fromhex(l.data[2:])
                remainder = int.from_bytes(b, 'big')
                self.assertEqual(remainder, int((1000000 - TAX_LEVEL) * (10 ** 32)))
                logg.debug('period {} remainder {}'.format(period, remainder))

        sink_balance = self.contract.functions.balanceOf(self.sink_address).call()
        logg.debug('{} {}'.format(sink_increment, sink_balance))
        self.assertEqual(sink_balance, int(sink_increment * 0.98))
        self.assertEqual(sink_balance, int(sink_increment * (1000000 - TAX_LEVEL) / 1000000))

        balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        self.assertEqual(balance, supply - sink_increment)


    def test_redistribution_two_of_ten(self):
        mint_amount = 100000000
        z = 0
        for i in range(10):
            self.contract.functions.mintTo(self.w3.eth.accounts[i], mint_amount).transact()
            z += mint_amount

        initial_balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()

        spend_amount = 1000000
        external_address = web3.Web3.toChecksumAddress('0x' + os.urandom(20).hex())
        self.contract.functions.transfer(external_address, spend_amount).transact({'from': self.w3.eth.accounts[1]})
        tx_hash = self.contract.functions.transfer(external_address, spend_amount).transact({'from': self.w3.eth.accounts[2]})
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        # No cheating!
        self.contract.functions.transfer(self.w3.eth.accounts[3], spend_amount).transact({'from': self.w3.eth.accounts[3]})
        # Cheapskate!
        self.contract.functions.transfer(external_address, spend_amount-1).transact({'from': self.w3.eth.accounts[4]})

        self.assertEqual(r.status, 1)

        self.eth_tester.time_travel(self.start_time + 61)

        self.contract.functions.applyDemurrage().transact()
        self.contract.functions.changePeriod().transact()

        bummer_balance = self.contract.functions.balanceOf(self.w3.eth.accounts[3]).call()
        self.assertEqual(bummer_balance, mint_amount - (mint_amount * (TAX_LEVEL / 1000000)))
        logg.debug('bal {} '.format(bummer_balance))

        bummer_balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        spender_balance = mint_amount - spend_amount
        spender_decayed_balance = int(spender_balance - (spender_balance * (TAX_LEVEL / 1000000)))
        self.assertEqual(bummer_balance, spender_decayed_balance)
        logg.debug('bal {} '.format(bummer_balance))

        tx_hash = self.contract.functions.applyRedistributionOnAccount(self.w3.eth.accounts[1]).transact()
        r = self.w3.eth.getTransactionReceipt(tx_hash)
        logg.debug('log {}'.format(r.logs))

        self.contract.functions.applyRedistributionOnAccount(self.w3.eth.accounts[2]).transact()

        redistribution_data = self.contract.functions.redistributions(0).call()
        logg.debug('redist data {}'.format(redistribution_data.hex()))

        account_period_data = self.contract.functions.accountPeriod(self.w3.eth.accounts[1]).call()
        logg.debug('account period {}'.format(account_period_data))

        actual_period = self.contract.functions.actualPeriod().call()
        logg.debug('period {}'.format(actual_period))

        redistribution = int((z / 2) * (TAX_LEVEL / 1000000))
        spender_new_base_balance = ((mint_amount - spend_amount) + redistribution)
        spender_new_decayed_balance = int(spender_new_base_balance - (spender_new_base_balance * (TAX_LEVEL / 1000000)))

        spender_actual_balance = self.contract.functions.balanceOf(self.w3.eth.accounts[1]).call()
        logg.debug('rrr {} {}'.format(redistribution, spender_new_decayed_balance))

        self.assertEqual(spender_actual_balance, spender_new_decayed_balance)


if __name__ == '__main__':
    unittest.main()

 
