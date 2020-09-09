"""
Launch the 6nimmt! client bot.

Created on Wed Aug 26 12:44:50 202
"""
import nimmt_lib as nimmt
import sys
import argparse

# Setup, and process arguments
parser = argparse.ArgumentParser()
parser.add_argument("-t", "--test", action="store_true",
                    help="read and respond to pseudo stdin from test file")
parser.add_argument("-n", "--name", default="penbot",
                    help="change the bot's name (default: 'penbot')")
parser.add_argument("-e", "--echo-input", action="store_true",
                    help="echo received messages into the log")
args = parser.parse_args()

the_game = nimmt.GameState(player_name=args.name, testing=args.test, echo_input=args.echo_input)

if args.test:
    input_stream = open('./tests/harness.stdin')
else:
    input_stream = sys.stdin

# Introduce self to the game
the_game.register_self()
# Read and react to stream input
for line in input_stream:
    the_game.build_messages(line)
    if the_game.status[0:5] == "ERROR":
        break

# Game terminated
if the_game.status[0:5] == 'ERROR':
    print("Something has gone wrong:\n" + the_game.status)
else:
    print("Final scores:")
    for k,v in the_game.players.items():
        print(k + " " + str(v.points))
