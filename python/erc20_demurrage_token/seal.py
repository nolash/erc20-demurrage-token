# standard imports
import enum

# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.jsonrpc import JSONRPCRequest
from chainlib.eth.tx import (
        TxFactory,
        TxFormat,
        )
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        abi_decode_single,
        )
from hexathon import (
        add_0x,
        )

class ContractState(enum.IntEnum):
    MINTER_STATE = 1
    SINK_STATE = 2
    EXPIRY_STATE = 4
    CAP_STATE = 8

CONTRACT_SEAL_STATE_MAX = 0

for v in dir(ContractState):
    if len(v) > 6 and v[-6:] == '_STATE':
       CONTRACT_SEAL_STATE_MAX += getattr(ContractState, v).value


class SealedContract(TxFactory):

    def seal(self, contract_address, sender_address, seal, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('seal')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(seal)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def is_sealed(self, contract_address, v, sender_address=ZERO_ADDRESS, id_generator=None):
        j = JSONRPCRequest(id_generator)
        o = j.template()
        o['method'] = 'eth_call'
        enc = ABIContractEncoder()
        enc.method('isSealed')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(v)
        data = add_0x(enc.get())
        tx = self.template(sender_address, contract_address)
        tx = self.set_code(tx, data)
        o['params'].append(self.normalize(tx))
        o['params'].append('latest')
        o = j.finalize(o)
        return o


    @classmethod
    def parse_is_sealed(self, v):
        return abi_decode_single(ABIContractType.BOOLEAN, v)
