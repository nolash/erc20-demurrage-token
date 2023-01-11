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
import datetime
import math

# external imports
import confini
import chainlib.eth.cli
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.tx import receipt
from chainlib.eth.constant import ZERO_ADDRESS
from hexathon import to_int as hex_to_int
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
    config.add(args.steps, '_STEPS', False)


arg_flags = ArgFlag()
arg = Arg(arg_flags)
flags = arg_flags.STD_WRITE | arg_flags.EXEC | arg_flags.WALLET

argparser = chainlib.eth.cli.ArgumentParser()
argparser = process_args(argparser, arg, flags)
argparser.add_argument('--steps', type=int, default=0, help='Max demurrage steps to apply per round')
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
    chain_spec = settings.get('CHAIN_SPEC')
    conn = settings.get('CONN')
    o = block_latest()
    r = conn.do(o)
 
    block_start_number = None
    try:
        block_start_number = hex_to_int(r)
    except TypeError:
        block_start_number = int(r)

    o = block_by_number(block_start_number)
    r = conn.do(o)

    block_start = Block(r)
    block_start_timestamp = block_start.timestamp
    block_start_datetime = datetime.datetime.fromtimestamp(block_start_timestamp)

    gas_oracle = settings.get('FEE_ORACLE')
    c = DemurrageToken(chain_spec, gas_oracle=gas_oracle)
    o = c.demurrage_timestamp(settings.get('EXEC'))
    r = conn.do(o)

    demurrage_timestamp = None
    try:
        demurrage_timestamp = hex_to_int(r)
    except TypeError:
        demurrage_timestamp = int(r)
    demurrage_datetime = datetime.datetime.fromtimestamp(demurrage_timestamp)

    total_seconds = block_start_timestamp - demurrage_timestamp
    total_steps = total_seconds / 60

    if total_steps < 1.0:
        logg.error('only {} seconds since last demurrage application, skipping'.format(total_seconds))
        return

    logg.debug('block start is at {} demurrage is at {} -> {} minutes'.format(
        block_start_datetime,
        demurrage_datetime,
        total_steps,
        ))

    rounds = 1
    if config.get('_STEPS') > 0:
        rounds = math.ceil(total_steps / config.get('_STEPS'))

    logg.info('will perform {} rounds of {} steps'.format(rounds, config.get('_STEPS')))

    last_tx_hash = None
    for i in range(rounds):
        signer = settings.get('SIGNER')
        signer_address = settings.get('SENDER_ADDRESS')

        nonce_oracle = settings.get('NONCE_ORACLE')

        c = DemurrageToken(chain_spec, signer=signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
        (tx_hash_hex, o) = c.apply_demurrage(config.get('_EXEC_ADDRESS'), signer_address, limit=config.get('_STEPS'))
        if settings.get('RPC_SEND'):
            print(tx_hash_hex)
            conn.do(o)
            if config.true('_WAIT_ALL') or (i == rounds - 1 and config.true('_WAIT')):
                r = conn.wait(tx_hash_hex)
                if r['status'] == 0:
                    sys.stderr.write('EVM revert while deploying contract. Wish I had more to tell you')
                    sys.exit(1)
        else:
            print(o)



if __name__ == '__main__':
    main()
