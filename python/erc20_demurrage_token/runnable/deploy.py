"""Deploy sarafu token

.. moduleauthor:: Louis Holbrook <dev@holbrook.no>
.. pgp:: 0826EDA1702D1E87C6E2875121D2E7BB88C2A746 

"""

# standard imports
import sys
import os
import json
import argparse
import logging

# external imports
import confini
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.dict import DictKeystore
from chainlib.chain import ChainSpec
from chainlib.eth.nonce import (
        RPCNonceOracle,
        OverrideNonceOracle,
        )
from chainlib.eth.gas import (
        RPCGasOracle,
        OverrideGasOracle,
        )
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.tx import receipt
from chainlib.eth.constant import ZERO_ADDRESS
import chainlib.eth.cli

# local imports
import erc20_demurrage_token
from erc20_demurrage_token import (
        DemurrageToken,
        DemurrageTokenSettings,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(__file__)
data_dir = os.path.join(script_dir, '..', 'data')

config_dir = os.path.join(data_dir, 'config')

arg_flags = chainlib.eth.cli.argflag_std_write
argparser = chainlib.eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--name', dest='token_name', type=str, help='Token name')
argparser.add_argument('--symbol', dest='token_symbol', required=True, type=str, help='Token symbol')
argparser.add_argument('--decimals', dest='token_decimals', default=18, type=int, help='Token decimals')
argparser.add_argument('--sink-address', dest='sink_address', default=ZERO_ADDRESS, type=str, help='demurrage level,ppm per minute') 
argparser.add_argument('--supply-limit', dest='supply_limit', type=int, help='token supply limit (0 = no limit)')
argparser.add_argument('--redistribution-period', type=int, help='redistribution period, minutes (0 = deactivate)') # default 10080 = week
argparser.add_argument('--multi', action='store_true', help='automatic redistribution')
argparser.add_argument('--demurrage-level', dest='demurrage_level', type=int, help='demurrage level, ppm per minute') 
args = argparser.parse_args()

arg_flags = chainlib.eth.cli.argflag_std_write

extra_args = {
        'redistribution_period': 'TOKEN_REDISTRIBUTION_PERIOD',
        'demurrage_level': 'TOKEN_DEMURRAGE_LEVEL',
        'supply_limit': 'TOKEN_SUPPLY_LIMIT',
        'token_name': 'TOKEN_NAME',
        'token_symbol': 'TOKEN_SYMBOL',
        'token_decimals': 'TOKEN_DECIMALS',
        'sink_address': 'TOKEN_SINK_ADDRESS',
        'multi': None,
        }
config = chainlib.eth.cli.Config.from_args(args, arg_flags, extra_args=extra_args, default_fee_limit=DemurrageToken.gas(), base_config_dir=config_dir)

if not bool(config.get('TOKEN_NAME')):
    logg.info('token name not set, using symbol {} as name'.format(config.get('TOKEN_SYMBOL')))
    config.add(config.get('TOKEN_SYMBOL'), 'TOKEN_NAME', True)

if config.get('TOKEN_SUPPLY_LIMIT') == None:
    config.add(0, 'TOKEN_SUPPLY_LIMIT', True)

if config.get('TOKEN_REDISTRIBUTION_PERIOD') == None:
    config.add(10800, 'TOKEN_REDISTRIBUTION_PERIOD', True)
logg.debug('config loaded:\n{}'.format(config))

wallet = chainlib.eth.cli.Wallet()
wallet.from_config(config)

rpc = chainlib.eth.cli.Rpc(wallet=wallet)
conn = rpc.connect_by_config(config)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))


def main():
    signer = rpc.get_signer()
    signer_address = rpc.get_sender_address()

    gas_oracle = rpc.get_gas_oracle()
    nonce_oracle = rpc.get_nonce_oracle()

    c = DemurrageToken(chain_spec, signer=signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
    settings = DemurrageTokenSettings()
    settings.name = config.get('TOKEN_NAME')
    settings.symbol = config.get('TOKEN_SYMBOL')
    settings.decimals = int(config.get('TOKEN_DECIMALS'))
    settings.demurrage_level = int(config.get('TOKEN_DEMURRAGE_LEVEL'))
    settings.period_minutes = int(config.get('TOKEN_REDISTRIBUTION_PERIOD'))
    settings.sink_address = config.get('TOKEN_SINK_ADDRESS')

    (tx_hash_hex, o) = c.constructor(
            signer_address,
            settings,
            redistribute=config.true('_MULTI'),
            cap=int(config.get('TOKEN_SUPPLY_LIMIT')),
            )
    if config.get('_RPC_SEND'):
        conn.do(o)
        if config.get('_WAIT'):
            r = conn.wait(tx_hash_hex)
            if r['status'] == 0:
                sys.stderr.write('EVM revert while deploying contract. Wish I had more to tell you')
                sys.exit(1)
            # TODO: pass through translator for keys (evm tester uses underscore instead of camelcase)
            address = r['contractAddress']

            print(address)
        else:
            print(tx_hash_hex)

    else:
        print(o)


if __name__ == '__main__':
    main()
