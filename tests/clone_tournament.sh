#!/bin/bash
# Usage: clone_tournament.sh USER SERVER NIMMTD_EXEC PORT

# Start the server
ssh $1@$2 $3 -p $4 &
read -t 0.6 -p "Launching server on port $4..."
echo ""
# Start the bots
socat TCP:${2}:$4 EXEC:"python ../pyclient/launch.py -e" 2>../logs/penbot.log &
socat TCP:${2}:$4 EXEC:"python ../pyclient/launch.py -n the_clone" 2>../logs/the_clone.log &
socat TCP:${2}:$4 EXEC:"python ../pyclient/launch.py -n dbl_or_nuttn" 2>../logs/dbl_or_nuttn.log &
# Start the control with manual input
socat - TCP:${2}:$4

