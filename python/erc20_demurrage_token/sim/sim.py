# external imports
from chainlib.eth.unittest.ethtester import create_tester_signer
from chainlib.eth.unittest.base import TestRPCConnection
from chainlib.eth.tx import receipt
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.address import to_checksum_address
from crypto_dev_signer.keystore.dict import DictKeystore
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from erc20_demurrage_token import DemurrageToken

class DemurrageTokenSimulation:

    def __init__(self, chain_spec, settings, redistribute=True, cap=0):
        self.accounts = []
        self.keystore = DictKeystore()
        self.signer = EIP155Signer(self.keystore)
        self.eth_helper = create_tester_signer(self.keystore)
        self.eth_backend = self.eth_helper.backend
        self.rpc = TestRPCConnection(None, self.eth_helper, self.signer)
        for a in self.keystore.list():
            self.accounts.append(add_0x(to_checksum_address(a)))
        settings.sink_address = self.accounts[0]

        nonce_oracle = RPCNonceOracle(self.accounts[0], conn=self.rpc)
        c = DemurrageToken(chain_spec, signer=self.signer, nonce_oracle=nonce_oracle)
        (tx_hash, o) = c.constructor(self.accounts[0], settings, redistribute=redistribute, cap=cap)
        self.rpc.do(o)
        o = receipt(tx_hash)
        r = self.rpc.do(o)
        if (r['status'] != 1):
            raise RuntimeError('contract deployment failed')
        self.address = r['contract_address']
