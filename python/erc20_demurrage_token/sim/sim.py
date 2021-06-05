# standard imports
import logging

# external imports
from chainlib.eth.unittest.ethtester import create_tester_signer
from chainlib.eth.unittest.base import TestRPCConnection
from chainlib.eth.tx import (
        receipt,
        Tx,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import (
        OverrideGasOracle,
        Gas,
        )
from chainlib.eth.address import to_checksum_address
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        )
from crypto_dev_signer.keystore.dict import DictKeystore
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from erc20_demurrage_token import DemurrageToken

logg = logging.getLogger(__name__)


class DemurrageTokenSimulation:

    def __init__(self, chain_spec, settings, redistribute=True, cap=0, actors=1):
        self.chain_spec = chain_spec
        self.accounts = []
        self.keystore = DictKeystore()
        self.signer = EIP155Signer(self.keystore)
        self.eth_helper = create_tester_signer(self.keystore)
        self.eth_backend = self.eth_helper.backend
        self.gas_oracle = OverrideGasOracle(limit=100000, price=1)
        self.rpc = TestRPCConnection(None, self.eth_helper, self.signer)
        self.period = 1
        for a in self.keystore.list():
            self.accounts.append(add_0x(to_checksum_address(a)))
        settings.sink_address = self.accounts[0]


        self.actors = []
        for i in range(actors):
            idx = i % 10
            address = self.keystore.new()
            self.actors.append(address)
            self.accounts.append(address)

            nonce_oracle = RPCNonceOracle(self.accounts[idx], conn=self.rpc)
            c = Gas(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
            (tx_hash, o) = c.create(self.accounts[idx], address, 100000 * 1000000)
            self.rpc.do(o)
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            if r['status'] != 1:
                raise RuntimeError('failed gas transfer to account #{}: {} from {}'.format(i, address, self.accounts[idx]))
            logg.debug('added actor account #{}: {}'.format(i, address))

        o = block_latest()
        r = self.rpc.do(o)
        self.last_block = r
        self.start_block = self.last_block

        o = block_by_number(r)
        r = self.rpc.do(o)
        self.last_timestamp = r['timestamp']
        self.start_timestamp = self.last_timestamp
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.rpc)

        c = DemurrageToken(chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], settings, redistribute=redistribute, cap=cap)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        if (r['status'] != 1):
            raise RuntimeError('contract deployment failed')
        self.address = r['contract_address']

        self.period_seconds = settings.period_minutes * 60

        self.last_block += 1
        self.last_timestamp += 1

        logg.info('intialized at block {} timestamp {} period {} demurrage level {} sink address {} (first address in keystore)'.format(
                self.last_block,
                self.last_timestamp,
                settings.period_minutes,
                settings.demurrage_level,
                settings.sink_address,
                )
            )

        self.eth_helper.disable_auto_mine_transactions()

        self.caller_contract = DemurrageToken(self.chain_spec)



    def mint(self, recipient, value):
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], recipient, value)
        self.rpc.do(o)
        logg.info('tx hash {}'.format(tx_hash))
        return tx_hash


    def transfer(self, sender, recipient, value):
        nonce_oracle = RPCNonceOracle(sender, conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        (tx_hash, o) = c.transfer(self.address, sender, recipient, value)
        self.rpc.do(o)
        return tx_hash


    def balance(self, holder):
        #o = self.caller_contract.balance_of(self.address, holder, sender_address=self.accounts[0])
        c = DemurrageToken(self.chain_spec)
        o = c.balance_of(self.address, holder, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        return self.caller_contract.parse_balance_of(r)


    def next(self):
        target_timestamp = self.period * self.period_seconds
        self.last_timestamp = target_timestamp

        self.eth_helper.mine_block()
    
        self.last_timestamp += 1
        o = block_by_number(self.last_block)
        r = self.rpc.do(o)
        self.last_block = r['number']
        block_base = self.last_block

        for tx_hash in r['transactions']:
            o = receipt(tx_hash)
            rcpt = self.rpc.do(o)
            if rcpt['status'] == 0:
                raise RuntimeError('tx {} (block {} index {}) failed'.format(tx_hash, self.last_block, rcpt['transaction_index']))
            logg.info('tx {} (block {} index {}) verified'.format(tx_hash, self.last_block, rcpt['transaction_index']))

        #self.eth_helper.time_travel(self.start_timestamp + self.last_timestamp)

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[0])
        self.rpc.do(o)
        #self.eth_helper.time_travel(self.start_timestamp + self.last_timestamp + 9)
        self.eth_helper.mine_block()
        self.last_block += 1

        (tx_hash, o) = c.change_period(self.address, self.accounts[0])
        self.rpc.do(o)
        #self.eth_helper.time_travel(self.start_timestamp + self.last_timestamp + 10)
        self.eth_helper.mine_block()
        self.last_block += 1

        o = block_by_number(self.last_block)
        r = self.rpc.do(o)
        for tx_hash in r['transactions']:
            o = receipt(tx_hash)
            rcpt = self.rpc.do(o)
            if rcpt['status'] == 0:
                raise RuntimeError('demurrage step failed on block {}'.format(self.last_block))

#        while True:
#            self.eth_helper.mine_block()
#            o = block_latest()
#            r = self.rpc.do(o)
#            self.last_block = r
#
#            o = block_by_number(r, include_tx=False)
#            r = self.rpc.do(o)
#            self.last_block =r['number']
#            if r['timestamp'] == target_timestamp:
#                break

        self.last_timestamp += self.last_block - block_base
        self.period += 1

        return (self.last_block, self.last_timestamp)
