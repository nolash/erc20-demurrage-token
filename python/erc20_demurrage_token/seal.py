# external imports
from chainlib.eth.tx import (
        TxFactory,
        TxFormat,
        )
from chainlib.eth.contract import (
        ABIContractEncoder,
        )

class SealedContract(TxFactory):

    def set_state(self, contract_address, sender_address, seal, tx_format=TxFormat.JSONRPC):
        enc = ABIContractEncoder()
        enc.method('seal')
        enc.typ(ABIContractType.UINT256)
        enc.uint256(seal)
        data = enc.get()
        tx = self.template(sender_address, contract_address, use_nonce=True)
        tx = self.set_code(tx, data)
        tx = self.finalize(tx, tx_format)
        return tx
