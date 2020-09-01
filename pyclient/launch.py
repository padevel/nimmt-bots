"""
Launch the 6nimmt! client bot.

Created on Wed Aug 26 12:44:50 202
"""
import nimmt_lib as nimmt
import sys

# Setup, and process arguments
run_as_test = False
for arg in sys.argv:
    if arg == 'test':
        run_as_test = True

the_game = nimmt.GameState(player_name="penbot")

if run_as_test:
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
