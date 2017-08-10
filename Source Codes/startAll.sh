#!/bin/bash
gnome-terminal --geometry 80x40+500+20 -e "/bin/bash -c 'cd ryu;./start_simple.sh' "
sleep 5
gnome-terminal --geometry 40x40+10+20 -e "/bin/bash -c 'sudo ./dnsProxy.py' "
sleep 8
gnome-terminal --geometry 40x10+10+500 -e "/bin/bash -c 'mn -c;sudo ./sectestTopo.py' "
sleep 8
gnome-terminal --geometry 80x40+500+20 -e "/bin/bash -c 'python CIv4.py' "










