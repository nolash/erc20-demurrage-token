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

# local imports
from erc20_demurrage_token import (
        DemurrageToken,
        DemurrageTokenSettings,
        )

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(__file__)
data_dir = os.path.join(script_dir, '..', 'data')

default_config_dir = os.environ.get('CONFINI_DIR', '/usr/local/share/sarafu-token')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', '--config', dest='c', type=str, default=default_config_dir, help='configuration directory')
argparser.add_argument('-p', '--provider', dest='p', default='http://localhost:8545', type=str, help='Web3 provider url (http only)')
argparser.add_argument('-w', action='store_true', help='Wait for the last transaction to be confirmed')
argparser.add_argument('-ww', action='store_true', help='Wait for every transaction to be confirmed')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, default='evm:ethereum:1', help='Chain specification string')
argparser.add_argument('-y', '--key-file', dest='y', type=str, help='Ethereum keystore file to use for signing')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('-d', action='store_true', help='Dump RPC calls to terminal and do not send')
argparser.add_argument('--name', type=str, help='Token name')
argparser.add_argument('--decimals', default=6, type=int, help='Token decimals')
argparser.add_argument('--gas-price', type=int, dest='gas_price', help='Override gas price')
argparser.add_argument('--nonce', type=int, help='Override transaction nonce')
argparser.add_argument('--sink-address', dest='sink_address', default=ZERO_ADDRESS, type=str, help='demurrage level,ppm per minute') 
argparser.add_argument('--supply-limit', dest='supply_limit', type=int, help='token supply limit (0 = no limit)')
argparser.add_argument('--redistribution-period', type=int, help='redistribution period, minutes (0 = deactivate)') # default 10080 = week
argparser.add_argument('--env-prefix', default=os.environ.get('CONFINI_ENV_PREFIX'), dest='env_prefix', type=str, help='environment prefix for variables to overwrite configuration')
argparser.add_argument('--symbol', type=str, help='Token symbol')
argparser.add_argument('--demurrage-level', dest='demurrage_level', type=int, help='demurrage level, ppm per minute') 
args = argparser.parse_args()

if args.vv:
    logg.setLevel(logging.DEBUG)
elif args.v:
    logg.setLevel(logging.INFO)

block_last = args.w
block_all = args.ww

# process config
config = confini.Config(args.c)
config.process()
args_override = {
            'TOKEN_REDISTRIBUTION_PERIOD': getattr(args, 'redistribution_period'),
            'TOKEN_DEMURRAGE_LEVEL': getattr(args, 'demurrage_level'),
            'TOKEN_SUPPLY_LIMIT': getattr(args, 'supply_limit'),
            'TOKEN_SYMBOL': getattr(args, 'symbol'),
            'TOKEN_NAME': getattr(args, 'name'),
            'TOKEN_DECIMALS': getattr(args, 'decimals'),
            'TOKEN_SINK_ADDRESS': getattr(args, 'sink_address'),
            'SESSION_CHAIN_SPEC': getattr(args, 'i'),
            'ETH_PROVIDER': getattr(args, 'p'),
        }
if config.get('TOKEN_NAME') == None:
    logg.info('token name not set, using symbol {} as name'.format(config.get('TOKEN_SYMBOL')))
    config.add(config.get('TOKEN_SYMBOL'), 'TOKEN_NAME', True)
config.dict_override(args_override, 'cli args')
logg.debug('config loaded:\n{}'.format(config))

passphrase_env = 'ETH_PASSPHRASE'
if args.env_prefix != None:
    passphrase_env = args.env_prefix + '_' + passphrase_env
passphrase = os.environ.get(passphrase_env)
if passphrase == None:
    logg.warning('no passphrase given')
    passphrase=''

signer_address = None
keystore = DictKeystore()
if args.y != None:
    logg.debug('loading keystore file {}'.format(args.y))
    signer_address = keystore.import_keystore_file(args.y, password=passphrase)
    logg.debug('now have key for signer address {}'.format(signer_address))
signer = EIP155Signer(keystore)

chain_spec = ChainSpec.from_chain_str(args.i)

rpc = EthHTTPConnection(args.p)
nonce_oracle = None
if args.nonce != None:
    nonce_oracle = OverrideNonceOracle(signer_address, args.nonce)
else:
    nonce_oracle = RPCNonceOracle(signer_address, rpc)

gas_oracle = None
if args.gas_price !=None:
    gas_oracle = OverrideGasOracle(price=args.gas_price, conn=rpc, code_callback=DemurrageToken.gas)
else:
    gas_oracle = RPCGasOracle(rpc, code_callback=DemurrageToken.gas)

dummy = args.d

token_name = args.name
if token_name == None:
    token_name = args.symbol

def main():
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
            redistribute=settings.period_minutes > 0,
            cap=int(config.get('TOKEN_SUPPLY_LIMIT')),
            )
    if dummy:
        print(tx_hash_hex)
        print(o)
    else:
        rpc.do(o)
        if block_last:
            r = rpc.wait(tx_hash_hex)
            if r['status'] == 0:
                sys.stderr.write('EVM revert while deploying contract. Wish I had more to tell you')
                sys.exit(1)
            # TODO: pass through translator for keys (evm tester uses underscore instead of camelcase)
            address = r['contractAddress']

            print(address)
        else:
            print(tx_hash_hex)


if __name__ == '__main__':
    main()
