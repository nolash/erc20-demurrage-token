# external imports
from chainlib.eth.tx import (
        TxFactory,
        TxFormat,
        )
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        abi_decode_single,
        )
from chainlib.eth.constant import ZERO_ADDRESS


class ExpiryContract(TxFactory):

    def set_expire_period(self, contract_address, sender_address, expire_timestamp, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('setExpirePeriod')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(expire_timestamp)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx


    def expires(self, contract_address, sender_address=ZERO_ADDRESS):
        return self.call_noarg('expires', contract_address, sender_address=sender_address)


    @classmethod
    def parse_expires(self, v):
        return abi_decode_single(ABIContractType.UINT256, v)


