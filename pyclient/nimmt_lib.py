import random
import sys

def err_print(*args, **kwargs):
    """Print to stderr i.l.o. stdout."""
    print(*args, file=sys.stderr, **kwargs)

def send_msg(header, body, testing=False):
    """Send a message to the server (via stdout)."""
    if testing:
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
    """A summary of the state of a game of 6nimmt!

    A game keeps track of what cards have been played, and the state
    of each stack in the play area. Each player's actions are also tracked individually
    using the 'Player' class.

    Classes:
    - Player: logging for a single player participating in the game

    Game evolution methods:
    - register_self(): declare 'self' to the game server
    - progress_game(): handle the most recent message from the server using the following methods
    - player_add(): instatiate a player, or update an existing player
    - new_hand(): reinitialise card tracking centrally and for each Player
    - update_stacks(): record the information provided by the server about the stacks
    - play_a_card(): choose a card and send to server, update central card tracking
    - update_played(): enact the action reported by the server for a player
    - update_scores(): record the scores reported by the server
    - choose_stack(): nominate a stack to replace when playing a low card

    Helper methods:
    - build_messages(line_received): construct complete messages from the lines recieved and
      send to 'progress_game()' when complete
    - update_cards_at_large(): recalculate which cards are yet to be seen in this hand
    - choose_card(): select a card from own hand to meet server request
    - summarise_scores(): gather recently-updated scores from Players and record in a string
    - log_game_update(): write a single-line summary of what has just happened (once per round)
    """

    class Player():
        """A player in the game.

        Players have a score, a count of cards in their hand, a record of what they've
        played this hand, and some stats summarising their behaviour and likely nature
        of the cards held.
        """

        def __init__(self, name, id, deck_size=104, cards_held_n=10, starting_points=66):
            """Create a player in the game.

            Player is populated with:
            - name: the name of the player (=name)
            - id: a unique, short name for the player (=id)
            - cards_held_n: the number of cards held (=cards_held_n)
            - played: an empty set of cards played
            - points: number of points held (=starting_points)
            - deck_size: size of the deck (=deck_size, used for stats calcs)
            - hand_avg_est: an estimate of the average card value held, based on played cards
            """

            self.name = name
            self.deck_size = deck_size
            self.deck_mean = (self.deck_size+1)/2
            self.played = set()
            self.cards_held_n = cards_held_n
            self.points = starting_points
            self.hand_avg_est = self.estimate_hand_avg()
            self.id = id
            # TODO: more math on cards played

        def estimate_hand_avg(self):
            """
            Estimate the average card value in the hand, based on cards played.

            Assumes typical initial hand of equispaced cards with mean of (deck_size+1)/2.
            NB: This means the estimate can exceed bounds of deck if initial hand is strongly skewed.
            """

            if self.cards_held_n > 0:
                return self.deck_mean + (self.deck_mean*len(self.played)-sum(list(self.played))) / self.cards_held_n
            else:
                return self.deck_mean

        def play(self,card):
            """Record playing the nominated card from the hand and update tracking."""

            self.played.add(card)
            self.cards_held_n -= 1
            self.hand_avg_est = self.estimate_hand_avg()

        # score() method is not currently needed as server provides absolute scores
        # and scoring/card playing logic is not implemented (yet?)
        # def score(self,points):
        #     """Update the player's score (decrement)."""
        #     self.points -= points

    def __init__(self, player_name, deck_size=104, hand_size=10, stack_count=4,
                 cards_played=set(), hand=set(), players = {}, stacks = [],
                 strategy_weights = {},
                 testing=False, echo_input=False):
        """Initialise a 6nimmt! game.

        Populate tracking data for a 6nimmt game:

        Game parameters:
        - hand_size: the number of cards dealt to each player for each hand
        - stack_count: the number of stacks used
        - deck_size: the size of the deck used
        - deck: a set of all cards in the deck
        - myname: the name of the 'self' Player

        State of the game:
        - cards_played: the set of all cards thus far played in this hand
        - cards_in_hand: the set of cards held in-hand by 'self'
        - cards_at_large: the set of cards not sighted in own hand or in list of played cards
        - players: a dictionary of all (tracked) Players
        - stacks: a list of lists, each list records the properties for a stack

        Strategies:
        - strategies: a dict of the available strategies

        Logging and debugging attributes:
        - history: a record of all messages received from the server
        - status: a message reported during the most recent game-evolving action
        - _testing: a switch for enabling 'test' features
        - _echo_input: a switch for echoing received messages into the stderr log
        - self.strings: a dictionary of strings and list of strings to help with populating the log
        """

        self.deck_size = deck_size
        self.deck = set(range(1, deck_size+1))
        self.hand_size = hand_size
        self.stack_count = stack_count
        self.cards_played = cards_played  # by all players
        self.cards_in_hand = hand
        self.myname = player_name
        self.cards_at_large = self.update_cards_at_large()
        self.players = players
        self.stacks = stacks
        self.status = "INITIALISED"
        self.history = []
        self._message_build = []
        self._testing = testing
        self._echo_input = echo_input
        self.strings={}
        self.strings["scores"] = ""
        self.strings["played"] = ["Starting condition, no cards played."]
        self.strings["stacks"] = ""
        self.strategies = self.build_strategies(strategy_weights)

    def update_cards_at_large(self):
        """Update the set of cards not yet sighted using cards_in_hand and cards_played."""
        return self.deck.difference(self.cards_played).difference(self.cards_in_hand)

    def register_self(self):
        """Add oneself as a player in the hosted game, and instatiate a Player for logging."""
        self.player_add([self.myname])
        send_msg(header="player", body=self.myname, testing=self._testing)

    def build_messages(self, line_received):
        """Keep reading lines until we have a complete server message."""
        self._message_build.append(line_received.rstrip())
        if line_received == '\n':
            self.progress_game()

    def player_add(self,player_names):
        """Add one or more players to the game (by name)."""
        player_names = player_names[0].split()
        assert len(set(player_names)) == len(player_names), "The list of player names has duplicates."
        for player_name in player_names:
            self.players.update({player_name: self.Player(player_name, deck_size = self.deck_size, id="temp")})
            self.summarise_scores()
        for n, k in enumerate(self.players):
            self.players[k].id = "P"+str(n+1)  # Number the playes in the (arbitrary) order that python iterates the players

    def new_hand(self,new_cards):
        """Reinitialise card tracking to start a new hand."""
        for k,v in self.players.items():
            v.__init__(name=k, id=v.id)
        self.played = set()
        self.hand = {int(card) for card in new_cards[0].split()}
        self.strings["played"] = ["Starting layout, no cards played."]
        self.summarise_scores()

    def update_stacks(self, stack_table):
        """Process the 'stacks' message form the server, and store data."""
        self.stacks = [list(map(int,row.split())) for row in stack_table]  # Still need to process
        self.strings["stacks"] = "(" + ") (".join([" ".join(str(element) for element in stack) for stack in self.stacks]) + ")"

    def choose_card(self):
        """Nominate a card to play at the request of server 'card?' message."""
        best_score = -99
        strategy_chosen = None
        for strategy in self.strategies:
            strategy_proposed = strategy['method']()  # (score, card, reason)
            weighted_score = strategy_proposed[0]*strategy['weight']
            if weighted_score > best_score:
                best_score = weighted_score
                strategy_chosen = strategy_proposed
        return strategy_chosen

    def play_a_card(self):
        """Choose a card, send nominated card to server, and update tracking."""
        score, card_selected, reason = self.choose_card()
        send_msg(header="card", body=str(card_selected), testing=self._testing)
        self.hand.remove(card_selected)
        self.status = "CARD?: Selected " + str(card_selected)+" with score " + str(score) + " because " + reason
        # TODO: name the strategy
        # TODO: embed the weight into the function

    def update_played(self, the_play):
        """Update tracking for a Player, and logging, based on 'played' message from server."""
        (player, card, stack) = the_play[0].split()
        card = int(card)
        stack = int(stack)
        self.players[player].play(card)
        self.played.add(card)
        self.cards_at_large = self.update_cards_at_large()
        self.strings["played"].append(self.players[player].id + ":" + str(card).rjust(3) + "->" + str(stack))

    def update_scores(self, score_list):
        """Update player scores based on server 'scores' message."""
        score_list = score_list[0].split()
        score_table = list(zip(score_list[::2],score_list[1::2]))
        for line in score_table:
            player = line[0]
            score = int(line[1])
            self.players[player].points = score
        self.summarise_scores()

    def summarise_scores(self):
        """Prepare a one-line score report string to help with logging."""
        self.strings["scores"] = ", ".join([self.players[player].name + ": "
                                            + str(self.players[player].points).rjust(2)
                                            for player in self.players])

    def choose_stack(self, method='lowest'):
        """Choose the stack to take when prompted with 'stack?'."""
        if method == 'random':
            chosen_stack = random.choice([1,2,3,4])
        else:  # method == 'lowest'
            lowest_score = 99
            for i,stack in enumerate(self.stacks):
                if stack[1] < lowest_score:
                    lowest_score=stack[1]
                    chosen_stack = i+1
        send_msg(header="stack", body=str(chosen_stack), testing=self._testing)

    def log_game_update(self):
        """Write out the bundled changes of who played what where, and current scores."""
        err_print(" | ".join((self.strings["scores"],
                              ", ".join(self.strings["played"]),
                              self.strings["stacks"])))
        self.strings["played"] = []

    def progress_game(self):
        """Using the most recent server message, move the game forward.

        Messages that don't require action are simply logged or initialised appropriately, i.e.
        'players', 'cards', 'played', 'scores', 'stacks', 'info'. Messages with a '?'
        require a response: i.e. 'card?', "stack?".
        """

        if self._echo_input:
            err_print("IH:  " + "\nIB:  ".join(self._message_build))

        # Set the status flag to a default
        self.status = "NOMINAL - Nothing of note yet."

        # Handle the different message types
        header = self._message_build[0]
        body = self._message_build[1:-1]

        if header == "players":
            self.player_add(body)
            err_print ("Players: " + ", ".join([v.name + " (" + v.id + ")" for k,v in self.players.items()]))
            self.status = "PLAYERS: Added one or more players."
        elif header == "cards":
            self.new_hand(body)
            err_print("Hand: " + ", ".join(str(card) for card in sorted(self.hand)))
            self.status = "CARDS: Dealt a new hand."
        elif header == "card?":
            self.play_a_card()
        elif header == "played":
            self.update_played(body)
            self.status = "PLAYED: Updated played cards."
        elif header == "scores":
            self.update_scores(body)
            self.log_game_update()
            self.status = "SCORE: Updated scores."
        elif header == "stacks":
            self.update_stacks(body)
            self.status = "STACKS: Updated the stacks."
        elif header == "stack?":
            self.choose_stack()
            self.status = "STACK?: Selected a stack."
        elif header == "info":
            err_print("info: " + "\n> ".join(body))
        else:
            assert False, "What is this message???"

        # Archive and clear the message just actioned
        self.history.append(self._message_build)
        self._message_build = []

        err_print(self.status)

    # Strategies
    def choose_random(self):
        """Identify the subjective value of playing a random card."""
        return (10,
                random.sample(self.hand,1)[0],
                'yolo')

    def choose_lowest(self):
        """Identify the subjective value of playing the lowest card."""
        # get score of lowest-pointed stack and lowest card number on a playable stack
        cheapest_stack = 99
        lowest_stack = self.deck_size*2
        # lowest_stack_count = 6
        for stack in self.stacks:
            if stack[1] < cheapest_stack:
                cheapest_stack=stack[1]
            if (stack[2] < lowest_stack) and (stack[0]<5):
                lowest_stack = stack[2]
                # lowest_stack_count = stack[0]
        my_lowest = min(list(self.hand))
        count_below_mine = sum(card < my_lowest for card in list(self.cards_at_large))

        # Value estimate for expecting to take a stack
        play_value = ((10/cheapest_stack)  # low points good. base of 10 for a 1-point stack
                      / ((count_below_mine+1) * (len(self.hand)*(len(self.players)-1)/self.deck_size)))  # How close my card is to the bottom (estimate)
        message = "Playing lowest card expecting to take a stack. (High value if card will likely score points this way anyway.)"

        if my_lowest > lowest_stack:
            play_value = -100
            message = "Playing lowest card might go on top of a stack. Lowest card is not special."

        return (play_value,
                my_lowest,
                message)

    def choose_highest(self):
        """Identify the subjective value of playing the highest card."""
        # Will likely go on top of a stack (not taking any), bad if the likely stack(s) are full, except if others must take a stack first
        # May expend a high card that is needed later...

        # identify which stack will likely land on
        my_highest = max(list(self.hand))

        highest_below_mine = 0
        count_below_mine = 10
        for stack in self.stacks:
            if (stack[2] < my_highest) and (stack[2] > highest_below_mine):
                highest_below_mine = stack[2]
                count_below_mine = stack[1]
        err_print([highest_below_mine, count_below_mine])

        play_value = 50-15*(count_below_mine-1)
        return (play_value,
                my_highest,
                'Playing highest, as it seems unlikely to take a stack.')

    def build_strategies(self, weights):
        """Create a dict of strategies choosing a card.

        Each strategy has the following structure:
         - key: strategy name (str)
         - weight: fixed weight from command line arguments, default 1.0
         - method: a method to process the game data and return a 'proposed play'
        A proposed play is a tuple (score, card, reason).
        """
        strategies = []
        strategies.append({'name': 'random', 'weight': weights.pop('random', 1.0), 'method': self.choose_random})
        strategies.append({'name': 'lowest', 'weight': weights.pop('lowest', 1.0), 'method': self.choose_lowest})
        strategies.append({'name': 'highest', 'weight': weights.pop('highest', 1.0), 'method': self.choose_highest})

        return strategies