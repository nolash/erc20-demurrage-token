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
        ABIContractDecoder,
        ABIContractType,
        abi_decode_single,
        )
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.jsonrpc import JSONRPCRequest
from eth_erc20 import ERC20
from hexathon import (
        add_0x,
        strip_0x,
        )
from dexif import from_fixed

# local imports
from erc20_demurrage_token.data import data_dir
from erc20_demurrage_token.seal import SealedContract
from erc20_demurrage_token.expiry import ExpiryContract

logg = logging.getLogger(__name__)


class DemurrageRedistribution:
    
    def __init__(self, v):
        d = ABIContractDecoder()
        v = strip_0x(v)
        d.typ(ABIContractType.UINT256)
        d.typ(ABIContractType.UINT256)
        d.typ(ABIContractType.BYTES32)
        d.val(v[:64])
        d.val(v[64:128])
        d.val(v[128:192])
        r = d.decode()

        self.period = r[0]
        self.value = r[1]
        self.demurrage = from_fixed(r[2])


    def __str__(self):
        return 'period {} value {} demurrage {}'.format(self.period, self.value, self.demurrage)


class DemurrageTokenSettings:

    def __init__(self):
        self.name = None
        self.symbol = None
        self.decimals = None
        self.demurrage_level = None
        self.period_minutes = None
        self.sink_address = None


    def __str__(self):
        return 'name {} demurrage level {} period minutes {} sink address {}'.format(
                self.name,
                self.demurrage_level,
                self.period_minutes,
                self.sink_address,
                )


class DemurrageToken(ERC20, SealedContract, ExpiryContract):

    __abi = {}
    __bytecode = {}

    def constructor(self, sender_address, settings, tx_format=TxFormat.JSONRPC, version=None):
        code = self.cargs(settings.name, settings.symbol, settings.decimals, settings.demurrage_level, settings.period_minutes, settings.sink_address, version=version)
        tx = self.template(sender_address, None, use_nonce=True)
        tx = self.set_code(tx, code)
        return self.finalize(tx, tx_format)


    @staticmethod
    def cargs(name, symbol, decimals, demurrage_level, period_minutes, sink_address, version=None):
        code = DemurrageToken.bytecode()
        enc = ABIContractEncoder()
        enc.string(name)
        enc.string(symbol)
        enc.uint256(decimals)
        enc.uint256(demurrage_level)
        enc.uint256(period_minutes)
        enc.address(sink_address)
        code += enc.get()
        return code


    @staticmethod
    def gas(code=None):
        return 6000000


    @staticmethod
    def abi():
        name = 'DemurrageTokenSingleNocap'
        if DemurrageToken.__abi.get(name) == None:
            f = open(os.path.join(data_dir, name + '.json'), 'r')
            DemurrageToken.__abi[name] = json.load(f)
            f.close()
        return DemurrageToken.__abi[name]


    @staticmethod
    def bytecode(version=None):
        name = 'DemurrageTokenSingleNocap'
        if DemurrageToken.__bytecode.get(name) == None:
            f = open(os.path.join(data_dir, name + '.bin'), 'r')
            DemurrageToken.__bytecode[name] = f.read()
            f.close()
        return DemurrageToken.__bytecode[name]


    def increase_allowance(self, contract_address, sender_address, address, value, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('increaseAllowance')
        enc.typ(ABIContractType.ADDRESS)
        enc.typ(ABIContractType.UINT256)
        enc.address(address)
        enc.uint256(value)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def decrease_allowance(self, contract_address, sender_address, address, value, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('decreaseAllowance')
        enc.typ(ABIContractType.ADDRESS)
        enc.typ(ABIContractType.UINT256)
        enc.address(address)
        enc.uint256(value)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    # backwards compatibility
    def add_minter(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        return self.add_writer(contract_address, sender_address, address, tx_format=tx_format)


    def add_writer(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('addWriter')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def set_max_supply(self, contract_address, sender_address, cap, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('setMaxSupply')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(cap)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    # backwards compatibility
    def remove_minter(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        return self.delete_writer(contract_address, sender_address, address, tx_format=tx_format)


    def delete_writer(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('deleteWriter')
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


    def burn(self, contract_address, sender_address, value, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('burn')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(value)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def total_burned(self, contract_address, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('totalBurned')
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def to_base_amount(self, contract_address, value, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
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
        o = j.finalize(o)
        return o


    def remainder(self, contract_address, parts, whole, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
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
        o = j.finalize(o)
        return o


    def redistributions(self, contract_address, idx, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
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
        o = j.finalize(o)
        return o


    def account_period(self, contract_address, address, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('accountPeriod')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def to_redistribution(self, contract_address, participants, demurrage_modifier, value, period, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toRedistribution')
        enc.typ(ABIContractType.UINT256)
        enc.typ_literal('int128')
        enc.typ(ABIContractType.UINT256)
        enc.typ(ABIContractType.UINT256)
        enc.uint256(participants)
        enc.uint256(demurrage_modifier)
        enc.uint256(value)
        enc.uint256(period)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o



    def to_redistribution_period(self, contract_address, redistribution, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toRedistributionPeriod')
        v = strip_0x(redistribution)
        enc.typ_literal('(uint32,uint72,uint64)')
        enc.bytes32(v[:64])
        enc.bytes32(v[64:128])
        enc.bytes32(v[128:192])
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


#    def to_redistribution_participants(self, contract_address, redistribution, sender_address=ZERO_ADDRESS, id_generator=None):
#        j = JSONRPCRequest(id_generator)
#        o = j.template()
#        o['method'] = 'eth_call'
#        enc = ABIContractEncoder()
#        enc.method('toRedistributionParticipants')
#        v = strip_0x(redistribution)
#        enc.typ_literal('(uint32,uint72,uint104)')
#        #enc.typ(ABIContractType.BYTES32)
#        enc.bytes32(v[:64])
#        enc.bytes32(v[64:128])
#        enc.bytes32(v[128:192])
#        data = add_0x(enc.get())
#        tx = self.template(sender_address, contract_address)
#        tx = self.set_code(tx, data)
#        o['params'].append(self.normalize(tx))
#        o['params'].append('latest')
#        o = j.finalize(o)
#        return o
#

    def to_redistribution_supply(self, contract_address, redistribution, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toRedistributionSupply')
        v = strip_0x(redistribution)
        enc.typ_literal('(uint32,uint72,uint64)')
        enc.bytes32(v[:64])
        enc.bytes32(v[64:128])
        enc.bytes32(v[128:192])
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def to_redistribution_demurrage_modifier(self, contract_address, redistribution, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('toRedistributionDemurrageModifier')
        v = strip_0x(redistribution)
        enc.typ_literal('(uint32,uint72,uint64)')
        enc.bytes32(v[:64])
        enc.bytes32(v[64:128])
        enc.bytes32(v[128:192])
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def base_balance_of(self, contract_address, address, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('baseBalanceOf')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def set_sink_address(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('setSinkAddress')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def apply_demurrage(self, contract_address, sender_address, limit=0, tx_format=TxFormat.JSONRPC):
        if limit == 0:
            return self.transact_noarg('applyDemurrage', contract_address, sender_address)

        enc = ABIContractEncoder()
        enc.method('applyDemurrageLimited')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(limit)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def change_period(self, contract_address, sender_address):
        return self.transact_noarg('changePeriod', contract_address, sender_address)


    def apply_redistribution_on_account(self, contract_address, sender_address, address, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('applyRedistributionOnAccount')
        enc.typ(ABIContractType.ADDRESS)
        enc.address(address)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx




    def tax_level(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('taxLevel', contract_address, sender_address=sender_address)


    def resolution_factor(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('resolutionFactor', contract_address, sender_address=sender_address)


    def actual_period(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('actualPeriod', contract_address, sender_address=sender_address)


    def period_start(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('periodStart', contract_address, sender_address=sender_address)


    def period_duration(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('periodDuration', contract_address, sender_address=sender_address)


    def demurrage_amount(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('demurrageAmount', contract_address, sender_address=sender_address)


    def demurrage_timestamp(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('demurrageTimestamp', contract_address, sender_address=sender_address)


    def max_supply(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('maxSupply', contract_address, sender_address=sender_address)


#    def grow_by(self, contract_address, value, period, sender_address=ZERO_ADDRESS, id_generator=None):
#        j = JSONRPCRequest(id_generator)
#        o = j.template()
#        o['method'] = 'eth_call'
#        enc = ABIContractEncoder()
#        enc.method('growBy')
#        enc.typ(ABIContractType.UINT256)
#        enc.typ(ABIContractType.UINT256)
#        enc.uint256(value)
#        enc.uint256(period)
#        data = add_0x(enc.get())
#        tx = self.template(sender_address, contract_address)
#        tx = self.set_code(tx, data)
#        o['params'].append(self.normalize(tx))
#        o['params'].append('latest')
#        o = j.finalize(o)
#        return o
#

    def decay_by(self, contract_address, value, period, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('decayBy')
        enc.typ(ABIContractType.UINT256)
        enc.typ(ABIContractType.UINT256)
        enc.uint256(value)
        enc.uint256(period)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def get_distribution(self, contract_address, supply, demurrage_amount, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('getDistribution')
        enc.typ(ABIContractType.UINT256)
        enc.typ_literal('int128')
        enc.uint256(supply)
        enc.uint256(demurrage_amount)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    def get_distribution_from_redistribution(self, contract_address, redistribution, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('getDistributionFromRedistribution')
        v = strip_0x(redistribution)
        enc.typ_literal('(uint32,uint72,uint64)')
        enc.bytes32(v[:64])
        enc.bytes32(v[64:128])
        enc.bytes32(v[128:192])
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o



    @classmethod
    def parse_actual_period(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_period_start(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_period_duration(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_demurrage_amount(self, v):
        #        return abi_decode_single(ABIContractType.UINT256, v)
        return from_fixed(v)


    @classmethod
    def parse_remainder(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_to_base_amount(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)

    
    @classmethod
    def parse_redistributions(self, v):
        return strip_0x(v)
        

    @classmethod
    def parse_account_period(self, v):
        return abi_decode_single(ABIContractType.ADDRESS, v)


    @classmethod
    def parse_to_redistribution_period(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_to_redistribution_item(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_supply_cap(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_grow_by(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_decay_by(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_get_distribution(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_tax_level(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_resolution_factor(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


    @classmethod
    def parse_total_burned(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


def bytecode(**kwargs):
    return DemurrageToken.bytecode(version=kwargs.get('version'))


def create(**kwargs):
    return DemurrageToken.cargs(
            kwargs['name'],
            kwargs['symbol'],
            kwargs['decimals'],
            kwargs['demurragelevel'],
            kwargs['redistributionperiod'],
            kwargs['sinkaddress'],
            version=kwargs.get('version'))


def args(v):
    if v == 'create':
        return (['name', 'symbol', 'decimals', 'demurragelevel', 'redistributionperiod', 'sinkaddress'], ['version'],)
    elif v == 'default' or v == 'bytecode':
        return ([], ['version'],)
    raise ValueError('unknown command: ' + v)
