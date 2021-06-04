# standard imports
import os
import logging

# external imports
from chainlib.eth.tx import (
        TxFactory,
        TxFormat,
        )
from chainlib.hash import keccak256_string_to_hex
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        abi_decode_single,
        )
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.jsonrpc import jsonrpc_template
from eth_erc20 import ERC20
from hexathon import (
        add_0x,
        strip_0x,
        )

# local imports
from erc20_demurrage_token.data import data_dir

logg = logging.getLogger(__name__)


class DemurrageTokenSettings:

    def __init__(self):
        self.name = None
        self.symbol = None
        self.decimals = None
        self.demurrage_level = None
        self.period_minutes = None
        self.sink_address = None


class DemurrageToken(ERC20):

    __abi = None
    __bytecode = None

    def constructor(self, sender_address, settings, redistribute=True, cap=0, tx_format=TxFormat.JSONRPC):
        if not redistribute or cap:
            raise NotImplementedError('token cap and sink only redistribution not yet implemented')
        code = DemurrageToken.bytecode()
        enc = ABIContractEncoder()
        enc.string(settings.name)
        enc.string(settings.symbol)
        enc.uint256(settings.decimals)
        enc.uint256(settings.demurrage_level)
        enc.uint256(settings.period_minutes)
        enc.address(settings.sink_address)
        code += enc.get()
        tx = self.template(sender_address, None, use_nonce=True)
        tx = self.set_code(tx, code)
        return self.finalize(tx, tx_format)


    @staticmethod
    def gas(code=None):
        return 3500000

    @staticmethod
    def abi():
        if DemurrageToken.__abi == None:
            f = open(os.path.join(data_dir, 'DemurrageTokenMultiNocap.json'), 'r')
            DemurrageToken.__abi = json.load(f)
            f.close()
        return DemurrageToken.__abi


    @staticmethod
    def bytecode():
        if DemurrageToken.__bytecode == None:
            f = open(os.path.join(data_dir, 'DemurrageTokenMultiNocap.bin'), 'r')
            DemurrageToken.__bytecode = f.read()
            f.close()
        return DemurrageToken.__bytecode


    def add_minter(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('addMinter')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def remove_minter(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('removeMinter')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def mint_to(self, contract_address, sender_address, address, value, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('mintTo')
        enc.typ(ABIContractType.ADDRESS)
        enc.typ(ABIContractType.UINT256)
        enc.address(address)
        enc.uint256(value)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def to_base_amount(self, contract_address, value, sender_address=ZERO_ADDRESS):
        o = jsonrpc_template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toBaseAmount')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(value)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        return o


    def remainder(self, contract_address, parts, whole, sender_address=ZERO_ADDRESS):
        o = jsonrpc_template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('remainder')
        enc.typ(ABIContractType.UINT256)
        enc.typ(ABIContractType.UINT256)
        enc.uint256(parts)
        enc.uint256(whole)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        return o


    def redistributions(self, contract_address, idx, sender_address=ZERO_ADDRESS):
        o = jsonrpc_template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('redistributions')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(idx)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        return o


    def to_redistribution_period(self, contract_address, redistribution, sender_address=ZERO_ADDRESS):
        o = jsonrpc_template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toRedistributionPeriod')
        enc.typ(ABIContractType.BYTES32)
        enc.bytes32(redistribution)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        return o


    def apply_demurrage(self, contract_address, sender_address):
        return self.transact_noarg('applyDemurrage', contract_address, sender_address)


    def change_period(self, contract_address, sender_address):
        return self.transact_noarg('changePeriod', contract_address, sender_address)


    def actual_period(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('actualPeriod', contract_address, sender_address=sender_address)


    def period_start(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('actualPeriod', contract_address, sender_address=sender_address)


    def period_duration(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('actualPeriod', contract_address, sender_address=sender_address)


    def demurrage_amount(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('demurrageAmount', contract_address, sender_address=sender_address)


    def parse_actual_period(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    def parse_period_start(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    def parse_period_duration(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    def parse_demurrage_amount(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    def parse_remainder(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    def parse_to_base_amount(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)

    
    def parse_redistributions(self, v):
        return abi_decode_single(ABIContractType.BYTES32, v)


    def parse_to_redistribution_period(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


