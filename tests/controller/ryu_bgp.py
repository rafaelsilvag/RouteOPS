import eventlet

# BGPSpeaker needs sockets patched
eventlet.monkey_patch()

# initialize a log handler
# this is not strictly necessary but useful if you get messages like:
#    No handlers could be found for logger "ryu.lib.hub"
import logging
import sys
log = logging.getLogger()
log.addHandler(logging.StreamHandler(sys.stderr))

from ryu.services.protocols.bgp.bgpspeaker import BGPSpeaker

prefix_list = []

def dump_remote_best_path_change(event):
    prefix = { 'remote_as': event.remote_as, 'prefix': event.prefix, 'nexthop': event.nexthop }
    prefix_list.append(prefix)
    print 'the best path changed:', event.remote_as, event.prefix,\
        event.nexthop, event.is_withdraw

def detect_peer_down(remote_ip, remote_as):
    print 'Peer down:', remote_ip, remote_as

if __name__ == "__main__":
    speaker = BGPSpeaker(as_number=65000, router_id='172.0.255.254',
                         best_path_change_handler=dump_remote_best_path_change,
                         peer_down_handler=detect_peer_down)

    speaker.neighbor_add('172.0.0.1', 65000, enable_ipv4=True, enable_vpnv4=True, is_next_hop_self=True)
    speaker.neighbor_add('172.0.0.2', 65000, enable_ipv4=True, enable_vpnv4=True, is_next_hop_self=True)
    speaker.neighbor_add('172.0.0.3', 65000, enable_ipv4=True, enable_vpnv4=True, is_next_hop_self=True)
    # uncomment the below line if the speaker needs to talk with a bmp server.
    # speaker.bmp_server_add('192.168.177.2', 11019)
    count = 1
    i_prefix_list = True
    while True:
        eventlet.sleep(5)
        print prefix_list
        if(i_prefix_list):
            for prefix in prefix_list:
                print prefix
                speaker.prefix_add(prefix['prefix'], next_hop=prefix['nexthop'])
            i_prefix_list = False
        #prefix = '10.20.' + str(count) + '.0/24'
        #print "add a new prefix", prefix
        #speaker.prefix_add(prefix)
        #count += 1
        if count == 4:
            speaker.shutdown()
            break
