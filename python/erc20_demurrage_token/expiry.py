# external imports
from chainlib.eth.tx import (
        TxFactory,
        TxFormat,
        )
from chainlib.eth.contract import (
        ABIContractEncoder,
        ABIContractType,
        )

class ExpiryContract(TxFactory):

    def set_expires(self, contract_address, sender_address, expire_timestamp, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('setExpires')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(expire_timestamp)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx
