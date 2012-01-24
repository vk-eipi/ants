#!/usr/bin/env sh
#python tcpclient.py bhickey.net 2081 "python NumDiffBot_005.py --log=DEBUG" vk_NumDiff21 taw 100
#python tcpclient.py bhickey.net 2081 "python ExploreBot.py --log=DEBUG" vk_Explore30 taw 20
#python tcpclient.py tcpants.com 2081 "python ExploreBot_002.py --log=DEBUG" vk_Explore31 taw1 50
python tcpclient.py tcpants.com 2081 "python $1.py --log=WARNING" vk_$1 taw1 10
