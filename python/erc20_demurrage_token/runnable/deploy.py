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

# local imports
import erc20_demurrage_token
from erc20_demurrage_token import (
        DemurrageToken,
        DemurrageTokenSettings,
        )

def process_config_local(config, arg, args, flags):
    config.add(args.name, 'TOKEN_NAME', False)
    config.add(args.symbol, 'TOKEN_SYMBOL', False)
    config.add(args.decimals, 'TOKEN_DECIMALS', False)
    config.add(args.sink_address, 'TOKEN_SINK_ADDRESS', False)
    config.add(args.redistribution_period, 'TOKEN_REDISTRIBUTION_PERIOD', False)
    config.add(args.demurrage_level, 'TOKEN_DEMURRAGE_LEVEL', False)
    #config.add(args.supply_limit, 'TOKEN_DECIMALS', False)


arg_flags = ArgFlag()
arg = Arg(arg_flags)
flags = arg_flags.STD_WRITE | arg_flags.EXEC | arg_flags.WALLET

argparser = chainlib.eth.cli.ArgumentParser()
argparser = process_args(argparser, arg, flags)
argparser.add_argument('--name', dest='token_name', type=str, help='Token name')
argparser.add_argument('--symbol', dest='token_symbol', required=True, type=str, help='Token symbol')
argparser.add_argument('--decimals', dest='token_decimals', type=int, help='Token decimals')
argparser.add_argument('--sink-address', dest='sink_address', type=str, help='demurrage level,ppm per minute') 
#argparser.add_argument('--supply-limit', dest='supply_limit', type=int, help='token supply limit (0 = no limit)')
argparser.add_argument('--redistribution-period', dest='redistribution_period', type=int, help='redistribution period, minutes (0 = deactivate)') # default 10080 = week
#argparser.add_argument('--multi', action='store_true', help='automatic redistribution')
argparser.add_argument('--demurrage-level', dest='demurrage_level', type=int, help='demurrage level, ppm per minute') 
args = argparser.parse_args()

logg = process_log(args, logg)

config = Config()
config = process_config(config, arg, args, flags)
config = process_config_local(config, arg, args, flags)
logg.debug('config loaded:\n{}'.format(config))

settings = ChainSettings()
settings = process_settings(settings, config)
logg.debug('settings loaded:\n{}'.format(settings))


def main():
    conn = settings.get('CONN')
    signer = settings.get('SIGNER')
    signer_address = settings.get('SENDER_ADDRESS')

    gas_oracle = settings.get('FEE_ORACLE')
    nonce_oracle = settings.get('NONCE_ORACLE')

    c = DemurrageToken(chain_spec, signer=signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
    token_settings = DemurrageTokenSettings()
    token_settings.name = config.get('TOKEN_NAME')
    token_settings.symbol = config.get('TOKEN_SYMBOL')
    token_settings.decimals = int(config.get('TOKEN_DECIMALS'))
    token_settings.demurrage_level = int(config.get('TOKEN_DEMURRAGE_LEVEL'))
    token_settings.period_minutes = int(config.get('TOKEN_REDISTRIBUTION_PERIOD'))
    token_settings.sink_address = config.get('TOKEN_SINK_ADDRESS')

    (tx_hash_hex, o) = c.constructor(
            signer_address,
            token_settings,
            redistribute=config.true('_MULTI'),
            cap=int(config.get('TOKEN_SUPPLY_LIMIT')),
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
