#  Author:
#  Rudiger Birkner (Networked Systems Group ETH Zurich)

## RouteServer-specific imports
import json
from netaddr import *
from peer import Peer

###
### Extended Route Server Object
###

class SDNRS():
    def __init__(self):
        self.server_ipc = None
        self.server_ipc_proxy = None
        self.peers = None
        self.participants = {}

def parse_config(config_file):

    # loading config file
    config = json.load(open(config_file, 'r'))

    '''
        Create RouteServer environment ...
    '''

    # create SDNRS object
    sdnrs = SDNRS()

    for participant_name in config:
        participant = config[participant_name]

        # create peer and add it to the route server environment
        sdnrs.participants[participant_name] = participant

    return sdnrs
