# standard imports
import logging

# external imports
from chainlib.chain import ChainSpec
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
        block_by_hash,
        )
from funga.eth.keystore.dict import DictKeystore
from funga.eth.signer import EIP155Signer
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from erc20_demurrage_token import DemurrageToken
from erc20_demurrage_token.sim.error import TxLimitException

logg = logging.getLogger(__name__)


class DemurrageTokenSimulation:

    def __init__(self, chain_str, settings, redistribute=True, cap=0, actors=1):
        self.chain_spec = ChainSpec.from_chain_str(chain_str)
        self.accounts = []
        self.redistribute = redistribute
        self.keystore = DictKeystore()
        self.signer = EIP155Signer(self.keystore)
        self.eth_helper = create_tester_signer(self.keystore)
        self.eth_backend = self.eth_helper.backend
        self.gas_oracle = OverrideGasOracle(limit=100000, price=1)
        self.rpc = TestRPCConnection(None, self.eth_helper, self.signer)
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
            logg.info('added actor account #{}: {} block {}'.format(i, address, r['block_number']))

        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], settings, redistribute=redistribute, cap=cap)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        if (r['status'] != 1):
            raise RuntimeError('contract deployment failed')
        self.address = r['contract_address']
        logg.info('deployed contract to {} block {}'.format(self.address, r['block_number']))

        o = block_latest()
        r = self.rpc.do(o)
        self.last_block = r
        self.start_block = self.last_block

        o = block_by_number(r)
        r = self.rpc.do(o)
        self.last_timestamp = r['timestamp']
        self.start_timestamp = self.last_timestamp

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.rpc)
        o = c.decimals(self.address, sender_address=self.accounts[0])
        r = self.rpc.do(o)
        self.decimals = c.parse_decimals(r)

        self.period_seconds = settings.period_minutes * 60

        self.period = 1
        self.period_txs = []
        self.period_tx_limit = self.period_seconds - 1
        self.sink_address = settings.sink_address

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
        self.caller_address = self.accounts[0]


    def __check_limit(self):
        if self.period_tx_limit == len(self.period_txs):
            raise TxLimitException('reached period tx limit {}'.format(self.period_tx_limit))


    def __check_tx(self, tx_hash):
        o = receipt(tx_hash)
        rcpt = self.rpc.do(o)
        if rcpt['status'] == 0:
            raise RuntimeError('tx {} (block {} index {}) failed'.format(tx_hash, self.last_block, rcpt['transaction_index']))
        logg.debug('tx {} block {} index {} verified'.format(tx_hash, self.last_block, rcpt['transaction_index']))


    def get_now(self):
        o = block_latest()
        r = self.rpc.do(o)
        o = block_by_number(r, include_tx=False)
        r = self.rpc.do(o)
        return r['timestamp']


    def get_minutes(self):
        t = self.get_now()
        return int((t - self.start_timestamp) / 60)


    def get_start(self):
        return self.start_timestamp


    def get_period(self):
        o = self.caller_contract.actual_period(self.address, sender_address=self.caller_address)
        r = self.rpc.do(o)
        return self.caller_contract.parse_actual_period(r)


    def get_demurrage(self):
        o = self.caller_contract.demurrage_amount(self.address, sender_address=self.caller_address)
        r = self.rpc.do(o)
        logg.info('demrrage amount {}'.format(r))
        return float(self.caller_contract.parse_demurrage_amount(r) / (10 ** 38))


    def get_supply(self):
        o = self.caller_contract.total_supply(self.address, sender_address=self.caller_address)
        r = self.rpc.do(o)
        supply = self.caller_contract.parse_total_supply(r)
        return supply


    def from_units(self, v):
        return v * (10 ** self.decimals)


    def mint(self, recipient, value):
        self.__check_limit()
        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        (tx_hash, o) = c.mint_to(self.address, self.accounts[0], recipient, value)
        self.rpc.do(o)
        self.__next_block()
        self.__check_tx(tx_hash)
        self.period_txs.append(tx_hash)
        logg.info('mint {} tokens to {} - {}'.format(value, recipient, tx_hash))
        return tx_hash


    def transfer(self, sender, recipient, value):
        nonce_oracle = RPCNonceOracle(sender, conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        (tx_hash, o) = c.transfer(self.address, sender, recipient, value)
        self.rpc.do(o)
        self.__next_block()
        self.__check_tx(tx_hash)
        self.period_txs.append(tx_hash)
        logg.info('transfer {} tokens from {} to {} - {}'.format(value, sender, recipient, tx_hash))
        return tx_hash


    def balance(self, holder, base=False):
        o = None
        if base:
            o = self.caller_contract.base_balance_of(self.address, holder, sender_address=self.caller_address)
        else:
            o = self.caller_contract.balance_of(self.address, holder, sender_address=self.caller_address)
        r = self.rpc.do(o)
        return self.caller_contract.parse_balance(r)


    def __next_block(self):
        hsh = self.eth_helper.mine_block()
        o = block_by_hash(hsh)
        r = self.rpc.do(o)

        for tx_hash in r['transactions']:
            o = receipt(tx_hash)
            rcpt = self.rpc.do(o)
            if rcpt['status'] == 0:
                raise RuntimeError('tx {} (block {} index {}) failed'.format(tx_hash, self.last_block, rcpt['transaction_index']))
            logg.debug('tx {} (block {} index {}) verified'.format(tx_hash, self.last_block, rcpt['transaction_index']))

        logg.debug('now at block {} timestamp {}'.format(r['number'], r['timestamp']))


    def next(self):
        target_timestamp = self.start_timestamp + (self.period * self.period_seconds)
        logg.info('warping to {}, {} from start {}'.format(target_timestamp, target_timestamp - self.start_timestamp, self.start_timestamp))
        self.last_timestamp = target_timestamp 

        o = block_latest()
        r = self.rpc.do(o)
        self.last_block = r
        o = block_by_number(r)
        r = self.rpc.do(o)
        cursor_timestamp = r['timestamp'] + 1

        nonce_oracle = RPCNonceOracle(self.accounts[2], conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)

        i = 0
        while cursor_timestamp < target_timestamp:
            logg.info('mining block on {}'.format(cursor_timestamp))
            (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[2])
            self.rpc.do(o)
            self.eth_helper.time_travel(cursor_timestamp + 60)
            self.__next_block()
            o = receipt(tx_hash)
            r = self.rpc.do(o)
            if r['status'] == 0:
                raise RuntimeError('demurrage fast-forward failed on step {} timestamp {} block timestamp {} target {}'.format(i, cursor_timestamp, target_timestamp))
            cursor_timestamp += 60*60 # 1 hour
            o = block_by_number(r['block_number'])
            b = self.rpc.do(o)
            logg.info('block mined on timestamp {} (delta {}) block number {}'.format(b['timestamp'], b['timestamp'] - self.start_timestamp, b['number']))
            i += 1

        
        (tx_hash, o) = c.apply_demurrage(self.address, self.accounts[2])
        self.rpc.do(o)

        nonce_oracle = RPCNonceOracle(self.accounts[3], conn=self.rpc)
        c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        (tx_hash, o) = c.change_period(self.address, self.accounts[3])
        self.rpc.do(o)
        self.eth_helper.time_travel(target_timestamp + 1)
        self.__next_block()
    
        o = block_latest()
        r = self.rpc.do(o)
        o = block_by_number(self.last_block)
        r = self.rpc.do(o)
        self.last_block = r['number']
        block_base = self.last_block
        logg.info('block before demurrage execution {} {}'.format(r['timestamp'], r['number']))

        if self.redistribute:
            for actor in self.actors:
                nonce_oracle = RPCNonceOracle(actor, conn=self.rpc)
                c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
                (tx_hash, o) = c.apply_redistribution_on_account(self.address, actor, actor)
                self.rpc.do(o)

            nonce_oracle = RPCNonceOracle(self.sink_address, conn=self.rpc)
            c = DemurrageToken(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
            (tx_hash, o) = c.apply_redistribution_on_account(self.address, self.sink_address, self.sink_address)
            self.rpc.do(o)

        self.__next_block()

        o = block_latest()
        self.last_block = self.rpc.do(o)

        o = block_by_number(self.last_block)
        r = self.rpc.do(o)
        for tx_hash in r['transactions']:
            o = receipt(tx_hash)
            rcpt = self.rpc.do(o)
            if rcpt['status'] == 0:
                raise RuntimeError('demurrage step failed on block {}'.format(self.last_block))

        self.last_timestamp = r['timestamp']
        logg.debug('next concludes at block {} timestamp {}, {} after start'.format(self.last_block, self.last_timestamp, self.last_timestamp - self.start_timestamp))
        self.period += 1
        self.period_txs = []

        return (self.last_block, self.last_timestamp)
