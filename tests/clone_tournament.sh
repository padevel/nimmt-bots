#!/bin/bash
# Usage: clone_tournament.sh USER SERVER NIMMTD_EXEC PORT

# Start the server
ssh $1@$2 $3 -p $4 &
read -t 2 -p "Launching server on port $4.\n"
# Start the bots
socat TCP:${2}:$4 EXEC:"python ../pyclient/launch.py" &
socat TCP:${2}:$4 EXEC:"python ../pyclient/launch.py -n the_clone" &
socat TCP:${2}:$4 EXEC:"python ../pyclient/launch.py -n dbl_or_nuttn" &
# Start the control with manual input
socat - TCP:${2}:$4

