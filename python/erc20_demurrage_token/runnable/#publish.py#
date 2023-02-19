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
from funga.eth.signer import EIP155Signer
from funga.eth.keystore.dict import DictKeystore
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
from chainlib.eth.cli.arg import (
        Arg,
        ArgFlag,
        process_args,
        )
from chainlib.eth.cli.config import (
        Config,
        process_config,
        )
from chainlib.eth.cli.log import process_log
from chainlib.eth.settings import process_settings
from chainlib.eth.address import to_checksum_address
from chainlib.settings import ChainSettings

from dexif import to_fixed

# local imports
import erc20_demurrage_token
from erc20_demurrage_token import (
        DemurrageToken,
        DemurrageTokenSettings,
        )

logg = logging.getLogger()

script_dir = os.path.dirname(__file__)
data_dir = os.path.join(script_dir, '..', 'data')

config_dir = os.path.join(data_dir, 'config')


def process_config_local(config, arg, args, flags):
    config.add(args.token_name, 'TOKEN_NAME')
    config.add(args.token_symbol, 'TOKEN_SYMBOL')
    config.add(args.token_decimals, 'TOKEN_DECIMALS')
    sink_address = to_checksum_address(args.sink_address)
    config.add(sink_address, 'TOKEN_SINK_ADDRESS')
    config.add(args.redistribution_period, 'TOKEN_REDISTRIBUTION_PERIOD')

    v = (1 - (args.demurrage_level / 1000000)) ** (1 / config.get('TOKEN_REDISTRIBUTION_PERIOD'))
    if v >= 1.0:
        raise ValueError('demurrage level must be less than 100%')
    demurrage_level = to_fixed(v)
    logg.info('v {} demurrage level {}'.format(v, demurrage_level))
    config.add(demurrage_level, 'TOKEN_DEMURRAGE_LEVEL')
    return config


arg_flags = ArgFlag()
arg = Arg(arg_flags)
flags = arg_flags.STD_WRITE | arg_flags.WALLET

argparser = chainlib.eth.cli.ArgumentParser(arg_flags)
argparser = process_args(argparser, arg, flags)
argparser.add_argument('--name', dest='token_name', type=str, help='Token name')
argparser.add_argument('--symbol', dest='token_symbol', required=True, type=str, help='Token symbol')
argparser.add_argument('--decimals', dest='token_decimals', type=int, help='Token decimals')
argparser.add_argument('--sink-address', dest='sink_address', type=str, help='demurrage level,ppm per minute') 
argparser.add_argument('--redistribution-period', type=int, help='redistribution period, minutes (0 = deactivate)') # default 10080 = week
argparser.add_argument('--demurrage-level', dest='demurrage_level', type=int, help='demurrage level, ppm per period') 
args = argparser.parse_args()

logg = process_log(args, logg)

config = Config()
config = process_config(config, arg, args, flags)
config = process_config_local(config, arg, args, flags)
logg.debug('config loaded:\n{}'.format(config))

settings = ChainSettings()
settings = process_settings(settings, config)
logg.debug('settings loaded:\n{}'.format(settings))


#extra_args = {
#        'redistribution_period': 'TOKEN_REDISTRIBUTION_PERIOD',
#        'demurrage_level': 'TOKEN_DEMURRAGE_LEVEL',
#        'supply_limit': 'TOKEN_SUPPLY_LIMIT',
#        'token_name': 'TOKEN_NAME',
#        'token_symbol': 'TOKEN_SYMBOL',
#        'token_decimals': 'TOKEN_DECIMALS',
#        'sink_address': 'TOKEN_SINK_ADDRESS',
#        'multi': None,
#        }
#config = chainlib.eth.cli.Config.from_args(args, arg_flags, extra_args=extra_args, default_fee_limit=DemurrageToken.gas(), base_config_dir=config_dir)
#
#if not bool(config.get('TOKEN_NAME')):
#    logg.info('token name not set, using symbol {} as name'.format(config.get('TOKEN_SYMBOL')))
#    config.add(config.get('TOKEN_SYMBOL'), 'TOKEN_NAME', True)
#
#if config.get('TOKEN_SUPPLY_LIMIT') == None:
#    config.add(0, 'TOKEN_SUPPLY_LIMIT', True)
#
#if config.get('TOKEN_REDISTRIBUTION_PERIOD') == None:
#    config.add(10800, 'TOKEN_REDISTRIBUTION_PERIOD', True)
#logg.debug('config loaded:\n{}'.format(config))
#
#wallet = chainlib.eth.cli.Wallet()
#wallet.from_config(config)
#
#rpc = chainlib.eth.cli.Rpc(wallet=wallet)
#conn = rpc.connect_by_config(config)
#
#chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

def main():
    conn = settings.get('CONN')
    c = DemurrageToken(
            settings.get('CHAIN_SPEC'),
            signer=settings.get('SIGNER'),
            gas_oracle=settings.get('FEE_ORACLE'),
            nonce_oracle=settings.get('NONCE_ORACLE'),
            )
    token_settings = DemurrageTokenSettings()
    token_settings.name = config.get('TOKEN_NAME')
    token_settings.symbol = config.get('TOKEN_SYMBOL')
    token_settings.decimals = int(config.get('TOKEN_DECIMALS'))
    token_settings.demurrage_level = int(config.get('TOKEN_DEMURRAGE_LEVEL'))
    token_settings.period_minutes = int(config.get('TOKEN_REDISTRIBUTION_PERIOD'))
    token_settings.sink_address = config.get('TOKEN_SINK_ADDRESS')

    (tx_hash_hex, o) = c.constructor(
            settings.get('SENDER_ADDRESS'),
            token_settings,
            )
    if settings.get('RPC_SEND'):
        conn.do(o)
        if config.true('_WAIT'):
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
