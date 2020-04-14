''' session with user '''

import logging
import time

from copy import deepcopy

from queues import TxQItem

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pb_cfg import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class Session():
    '''
        Session between user and bot.
        It is volatile, will be lost after a timeout or disconection.
    '''
    TIMEOUT = 60

    def __init__(self, output_q=None):

        if not output_q:
            raise "Output queue needed !"

        self.messages = []
        self.alive_timestamp = time.time()
        self.state = None

        self.with_user = None
        self.with_chat = None

        self.output_q = output_q

    def iterate(self, *args, **kwargs):
        self.alive_timestamp = time.time()

    def end_sesion(self):

        if self.with_chat and self.output_q:
            # Send timeout message
            self.output_q.put(
                TxQItem(func_call='send_message',
                        args=(self.with_chat, "Timeout! Bye Bye !!"))
            )


class SelectGameSession(Session):
    '''
        Session to start a new game
    '''
    # States:
    S_FIRST_CONTACT = 0
    S_OFFER_GAMES = 1
    S_GAME_OFFER_RESPONSE = 2
    S_GAME_SELECTED = 3
    S_CREATE_GAME_INSTANCE = 4
    S_GAME_INSTANCE_CREATED = 5
    S_REDIRECT_USER = 6
    S_EXIT = 7
    S_ERROR = -1

    GAMES = [
        {'name': 'Guess the picture', 'ID': 0},
        {'name': 'Dominos', 'ID': 1},
        {'name': 'Laser fights', 'ID': 2},
        {'name': 'Sleeper', 'ID': 3},

    ]

    def __init__(self, intit_state=S_FIRST_CONTACT, output_q=None):

        super().__init__(output_q)

        self.state = intit_state

        self.game_selected = None

    def iterate(self, *args, **kwargs):
        '''
            Given args and kwargs move the state machine if possible
        '''

        super().iterate(*args, **kwargs)

        while True:

            if self.state == self.S_FIRST_CONTACT:
                if 'update' not in kwargs:
                    self.state = self.S_ERROR
                    continue
                msg = kwargs['update'].message
                text = '''Welcome ! I am the Game Master !\nWhat game you would like to play ?'''
                keyboard_markup = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(game['name'], callback_data=game['ID'])] for game in self.GAMES
                    ]
                )

                self.output_q.put(
                    TxQItem(func_call='send_message',
                            args=(msg.chat.id, text),
                            kwargs={'reply_markup': deepcopy(keyboard_markup)}
                            )
                )
                self.state = self.S_GAME_OFFER_RESPONSE

                self.with_chat = msg.chat.id
                self.with_user = msg.from_user.id
                return True

            elif self.state == self.S_OFFER_GAMES:
                pass
            elif self.state == self.S_GAME_OFFER_RESPONSE:
                logger.debug('Hi !'.format())
                if 'update' not in kwargs \
                        or not kwargs['update'].callback_query:
                    self.state = self.S_ERROR
                    continue

                upd = kwargs['update']
                query = upd.callback_query

                # It is mandatory to answer callback querries
                self.output_q.put(
                    TxQItem(func_call='answer_callback_query',
                            args=[query.id], kwargs={})
                )

                # Get user selection
                if not query.data or query.data == "" or int(query.data) >= len(self.GAMES):
                    # Strange answer
                    # Ignore it
                    return

                # Delete the inline keyboard after the repply
                self.output_q.put(
                    TxQItem(func_call='edit_message_reply_markup',
                            kwargs={'chat_id': query.message.chat.id, 'message_id': query.message.message_id, 'reply_markup': None})
                )

                self.game_selected = int(query.data)
                self.state = self.S_GAME_SELECTED

            elif self.state == self.S_GAME_SELECTED:
                if self.game_selected is None:
                    self.state = self.S_ERROR
                    logger.error('No game selected !')
                    continue

                text = "Great ! You have selected {}".format(
                    self.GAMES[self.game_selected]['name'])

                self.output_q.put(
                    TxQItem(func_call='send_message',
                            args=(self.with_chat, text))
                )

                self.state = self.S_CREATE_GAME_INSTANCE

            elif self.state == self.S_CREATE_GAME_INSTANCE:

                self.output_q.put(
                    TxQItem(func_call='send_message',
                            args=(
                                self.with_chat,
                                'Creating new game instance for {}'.format(
                                    self.GAMES[self.game_selected]['name'])
                            ))
                )
                pass

            elif self.state == self.S_GAME_INSTANCE_CREATED:
                pass
            elif self.state == self.S_REDIRECT_USER:
                pass
            elif self.state == self.S_EXIT:
                pass
            elif self.state == self.S_ERROR:
                logger.error('Entered in error state !'.format())
                break
