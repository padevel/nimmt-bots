import random
import sys

run_as_test = False  # FLAG

def err_print(*args, **kwargs):
    """Print to stderr i.l.o. stdout."""
    print(*args, file=sys.stderr, **kwargs)

def send_msg(header, body):
    """Send the message to the server (via stdout)."""
    if run_as_test:
        header_prefix = "OH: "
        body_prefix = "OB: "
    else:
        header_prefix = ""
        body_prefix = ""

    print(header_prefix + header)
    for line in body.split('\n'):
        print(body_prefix + line)
    print(body_prefix + "", flush=True)

class GameState():
    """Structure containing the current state of a game"""

    class Player():
        """A player in the game."""
        def __init__(self, name, deck_size=104, cards_held_n=10, starting_points=66):
            self.name = name
            self.played = set()
            self.cards_held_n = cards_held_n
            self.points = starting_points
            # TODO: math on cards played

        def play(self,card):
            """Play the designated card from the hand."""
            self.played.add(card)
            self.cards_held_n -= 1

        # def score(self,points):
        #     """Update the player's score (decrement)."""
        #     self.points -= points

    def __init__(self, deck=set(range(1, 104+1)), hand_size=10, player_name="",
                 cards_played=set(), hand=set(), players = {}, stacks = []):
        self.deck = deck
        self.hand_size = hand_size
        self.cards_played = cards_played # by all players
        self.cards_in_hand = hand
        self.myname = player_name
        self.update_cards_at_large()
        self.players = players
        self.stacks = stacks
        self.status = "INITIALISED"
        self.history = []
        self._message_build = []

    def update_cards_at_large(self):
        self.cards_at_large = self.deck.difference(self.cards_played).difference(self.cards_in_hand)

    def register_self(self):
        """Add oneself as a player in the hosted game."""
        self.player_add([self.myname])
        send_msg(header="player", body=self.myname)

    def build_messages(self, line_received):
        """Keep reading lines until we have a complete server message."""
        self._message_build.append(line_received.rstrip())
        if line_received == '\n':
            self.progress_game()

    def player_add(self,player_names):
        """Add a player to the game (by name)."""
        for player_name in player_names[0].split():
            self.players.update({player_name: self.Player(player_name)})

    def new_hand(self,new_cards):
        for k,v in self.players.items():
            v.__init__(name=k)
        self.played = set()
        self.hand = {int(card) for card in new_cards[0].split()}

    def update_stacks(self, stack_table):
        self.stacks = stack_table  # Still need to process

    def choose_card(self):
        return(random.sample(self.hand,1)[0])

    def play_a_card(self):
        card_selected = self.choose_card()
        send_msg(header="card", body=str(card_selected))
        self.hand.discard(card_selected)
    
    def update_played(self, the_plays):
        for play in the_plays:
            (player, card, stack) = play.split()
            card = int(card)
            stack = int(stack)
            self.players[player].play(card)
            self.played.update({card})
            self.cards_at_large.difference({card})

    def update_scores(self, score_list):
        score_list = score_list[0].split()
        score_table = list(zip(score_list[::2],score_list[1::2]))
        for line in score_table:
            player = line[0]
            score = int(line[1])
            self.players[player].points = score 
            err_print(self.players[player].name + ": " + str(self.players[player].points))

    def choose_stack(self):
        chosen_stack = random.choice([1,2,3,4])
        send_msg(header="stack", body=str(chosen_stack))
        # TODO: Pick the lowest score

    def progress_game(self):
        """Using the most recent server message, move the game forward."""

        echo_input = False  # FLAG
        if echo_input:
            if run_as_test:
                print("IH:  " + "\nIB:  ".join(self._message_build))
            else:
                err_print("IH:  " + "\nIB:  ".join(self._message_build))

        # Set the status flag to a default
        self.status = "NOMINAL - Nothing of note yet."

        # Handle the different message types
        header = self._message_build[0]
        body = self._message_build[1:-1]

        if header == "players":
            self.player_add(body)
            err_print ("Players: " + ", ".join([v.name for k,v in self.players.items()]))
            self.status = "PLAYERS: Added one or more players."
        elif header == "cards":
            self.new_hand(body)
            self.status = "CARDS: Dealt a new hand."
            err_print("Hand: " + ", ".join(str(card) for card in self.hand))
        elif header == "stacks":
            self.update_stacks(body)
            err_print(self.stacks)
            self.status = "STACKS: Updated the stacks."
        elif header == "card?":
            self.play_a_card()
            self.status = "CARD?: Selected a card."
        elif header == "played":
            self.update_played(body)
            self.status = "PLAYED: Updated played cards."
        elif header == "scores":
            self.update_scores(body)
            self.status = "SCORE: Updated scores."
        elif header == "stack?":
            self.choose_stack()
            self.status = "STACK?: Selected a stack."
        elif header == "info":
            pass
        else:
            assert False, "What is this???"
        
        # Archive and clear the message just actioned
        self.history.append(self._message_build)
        self._message_build = []