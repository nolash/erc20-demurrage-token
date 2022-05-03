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
from chainlib.eth.block import (
        block_latest,
        block_by_number,
        Block,
        )
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.tx import receipt
from chainlib.eth.constant import ZERO_ADDRESS
import chainlib.eth.cli
from hexathon import to_int as hex_to_int

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

arg_flags = chainlib.eth.cli.argflag_std_write | chainlib.eth.cli.Flag.EXEC
argparser = chainlib.eth.cli.ArgumentParser(arg_flags)
argparser.add_argument('--steps', type=int, default=0, help='Max demurrage steps to apply per round')
args = argparser.parse_args()
config = chainlib.eth.cli.Config.from_args(args, arg_flags, default_fee_limit=DemurrageToken.gas(), base_config_dir=config_dir)
config.add(args.steps, '_STEPS', False)
logg.debug('config loaded:\n{}'.format(config))

wallet = chainlib.eth.cli.Wallet()
wallet.from_config(config)

rpc = chainlib.eth.cli.Rpc(wallet=wallet)
conn = rpc.connect_by_config(config)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))


def main():
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

    gas_oracle = rpc.get_gas_oracle()
    c = DemurrageToken(chain_spec, gas_oracle=gas_oracle)
    o = c.demurrage_timestamp(config.get('_EXEC_ADDRESS'))
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
        signer = rpc.get_signer()
        signer_address = rpc.get_sender_address()

        nonce_oracle = rpc.get_nonce_oracle()

        c = DemurrageToken(chain_spec, signer=signer, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle)
        (tx_hash_hex, o) = c.apply_demurrage(config.get('_EXEC_ADDRESS'), signer_address, limit=config.get('_STEPS'))
        if config.get('_RPC_SEND'):
            print(tx_hash_hex)
            conn.do(o)
            if config.get('_WAIT_ALL') or (i == rounds - 1 and config.get('_WAIT')):
                r = conn.wait(tx_hash_hex)
                if r['status'] == 0:
                    sys.stderr.write('EVM revert while deploying contract. Wish I had more to tell you')
                    sys.exit(1)
        else:
            print(o)



if __name__ == '__main__':
    main()
