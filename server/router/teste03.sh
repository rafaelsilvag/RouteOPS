#!/bin/bash
#  Author:
#	Rafael S. Guimaraes <rafaelg@ifes.edu.br>
#
MAC_R01="08:00:27:89:3b:9f"
MAC_R02="08:00:27:92:18:1f"
MAC_R03="08:00:27:54:56:ea"
EXABGP="82:f1:5a:5d:d2:b8"
function start(){
  echo "Starting Rules..."
  sudo ovs-ofctl -O OpenFlow13 add-flow s1 "priority=31,in_port=3,dl_type=0x800,dl_dst=08:00:27:89:3b:9f,nw_dst=100.0.0.0/255.255.255.0,action=mod_dl_dst:08:00:27:92:18:1f,output:2"
  sudo ovs-ofctl -O OpenFlow13 add-flow s1 "priority=31,in_port=3,dl_type=0x800,dl_dst=08:00:27:89:3b:9f,nw_dst=100.0.1.0/255.255.255.0,action=mod_dl_dst:08:00:27:92:18:1f,output:2"
}
function stop(){
  echo "Stopping Rules...."
}
case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart|reload)
    stop
    start
    ;;
  *)
    echo $"Usage: $0 {start|stop|restart}"
    exit 1
esac
