"""
Launch a 6nimmt! client bot.

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
parser.add_argument("-w", "--weights",
                    help="set weights for each strategy, comma-separated <name>=<weight>")
args = parser.parse_args()

if args.weights:
    weights = {weight.split("=")[0]: float(weight.split("=")[1]) for weight in args.weights.split(",")}
else:
    weights = {}

the_game = nimmt.GameState(player_name=args.name, testing=args.test, echo_input=args.echo_input, strategy_weights=weights)

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
    nimmt.err_print("Something has gone wrong:\n" + the_game.status)
else:
    final_scores_str = ", ".join([k + " " + str(v.points) for k,v in the_game.players.items()])
    nimmt.err_print("Final scores:")
    nimmt.err_print(", ".join([k + " " + str(v.points) for k,v in the_game.players.items()]))
    # TODO: append single-line scores to score log file if name == "penbot"
