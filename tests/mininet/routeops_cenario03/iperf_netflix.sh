#!/bin/bash

for i in $(seq 0 30);do
    idc=4
    ((i_final=i+1))
    echo "[  $idc]   $i.00-$i_final.00   sec  0.00 Bytes  0.00 bits/sec    0   0.0 KBytes"
    sleep 1
    if [ $i -eq 30 ]
    then
        iperf3 -u -c 200.0.1.1 -B 150.0.0.200 -p 4322 -t 220 -b 0 -R
    fi
    ((i=i+20))
done
