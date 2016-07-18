#!/bin/bash

for i in $(seq 0 150);do
    idc=4
    ((i_final=i+1))
    echo "[  $idc]   $i.00-$i_final.00   sec  0.00 Bytes  0.00 bits/sec    0   0.0 KBytes"
    sleep 1
    if [ $i -eq 5 ]||[ $i -eq 25 ]||[ $i -eq 60 ]||[ $i -eq 90 ]||[ $i -eq 120 ]||[ $i -eq 150 ]
    then
        iperf3 -c 200.0.0.1 -B 150.0.0.1 -p 4323 -b 0 -t 15 -R
    fi
    ((i=i+20))
done
