''' Abstraction layer for the telegram api '''

import time
import logging
from threading import Lock, Thread

from telegram import Bot
from telegram.ext import Updater, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters

from pb_cfg import LOGGER_NAME
from pvt_cfg import TELEGRAM_API_TOKEN
from queues import OUTBOUND_MSG_QUEUE, INBOUND_MSG_QUEUE, RxQItem, TxQItem


logger = logging.getLogger(LOGGER_NAME)


class TelegramAbstractionLayer():
    ''' I/O with telegram server '''

    def __init__(self, api_key):

        self._exit_lock = Lock()

        self._api_key = api_key
        # 'Bot' telegram instance
        self._bot = None
        self._tx_thread = None
        # 'Updater' telegram instance
        self._rx_thread = None

    def start(self):
        ''' start the main loop '''

        logger.info('Staring {}'.format(type(self).__name__))

        if not self._exit_lock.acquire(blocking=False) \
                or self._tx_thread is not None \
                or self._rx_thread is not None:
            logger.fatal('Thread for {} is already running !'.format(
                type(self).__name__))
            return False

        try:
            self._bot = Bot(self._api_key)
            self._rx_thread = Updater(self._api_key, use_context=True)
        except Exception as ex:
            logger.fatal('Could not start {}! Error: {}'.format(
                type(self).__name__, ex))
            return False

        self._tx_thread = Thread(target=self._run)
        self._tx_thread.daemon = True
        self._tx_thread.start()

        # Handler for callback querries
        self._rx_thread.dispatcher.add_handler(
            CallbackQueryHandler(self.callback_query_handler))

        # Handler for all commands
        self._rx_thread.dispatcher.add_handler(
            MessageHandler(Filters.regex(r'/.*'), self.command_handler))

        # Handler for all non-commands
        self._rx_thread.dispatcher.add_handler(MessageHandler(
            Filters.regex(r'.*'), self.non_command_handler))

        logger.info('Staring {}:_rx_thread'.format(type(self).__name__))
        self._rx_thread.start_polling()

        return True

    def non_command_handler(self, update, context):
        ''' forward text messages '''
        logger.debug('TXT {}: {}'.format(
            update.message.message_id, update.message.text))

        # Attempt to get the IDs
        if update.message:
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id
        elif update.edited_message:
            # TODO should we take in eddited messages ?
            return
        else:
            logger.error('Received update without message: {}'.format(update))
            return

        INBOUND_MSG_QUEUE.put(RxQItem(
            RxQItem.TEXT_MSG,
            route_by=RxQItem.ROUTE_BY_CHAT_ID | RxQItem.ROUTE_BY_USER_ID,
            chat_id=chat_id,
            user_id=user_id,
            args=[update]))
        # Context seems to contain a lock so it cannot be pickled not put into a q
        # args=[update, context]))

    def command_handler(self, update, context):
        ''' forward command messages '''
        logger.debug('CMD {}: {}'.format(
            update.message.message_id, update.message.text))

        # Attempt to get the IDs
        if update.message:
            chat_id = update.message.chat.id
            user_id = update.message.from_user.id
        elif update.edited_message:
            # TODO should we take in eddited messages ?
            return
        else:
            logger.error('Received update without message: {}'.format(update))
            return

        INBOUND_MSG_QUEUE.put(RxQItem(
            RxQItem.COMMAND_MSG,
            route_by=RxQItem.ROUTE_BY_CHAT_ID | RxQItem.ROUTE_BY_USER_ID,
            chat_id=chat_id,
            user_id=user_id,
            args=[update]))
        # Context seems to contain a lock so it cannot be pickled not put into a q
        # args=[update, context]))

    def callback_query_handler(self, update, context):
        ''' forward callback messages '''
        logger.debug('CBK QRY {}: {}'.format(
            update.message.message_id, update.message.text))

        # Attempt to get the IDs
        if update.callback_query:
            chat_id = update.callback_query.chat_instance
            user_id = update.callback_query.from_user.id
        else:
            logger.error(
                'Received update without callback_query: {}'.format(update))
            return

        INBOUND_MSG_QUEUE.put(RxQItem(
            RxQItem.CALLBACK_QUERY_MSG,
            route_by=RxQItem.ROUTE_BY_CHAT_ID | RxQItem.ROUTE_BY_USER_ID,
            chat_id=chat_id,
            user_id=user_id,
            args=[update]))
        # Context seems to contain a lock so it cannot be pickled not put into a q
        # args=[update, context]))

    def stop(self):
        ''' stop the main loop '''
        if not self._exit_lock.locked():
            logger.error('Thread for {} is not currently running !'.format(
                type(self).__name__))
            return False
        elif self._tx_thread is None:
            logger.error('Thread for {} does not exist !'.format(
                type(self).__name__))
            return False
        else:

            # Stop the bot
            self._exit_lock.release()

            logger.info('Stopping {}:{}'.format(
                type(self).__name__, "_rx_thread"))
            # Stop the updater
            self._rx_thread.stop()

            # Ensure bot has been stopped
            self._tx_thread.join()

    def _run(self):
        ''' main loop '''
        logger.info('Staring {}:_tx_thread'.format(type(self).__name__))
        while True:

            # Pop output_q and send the messages
            if not OUTBOUND_MSG_QUEUE.empty():
                msg = OUTBOUND_MSG_QUEUE.get()

                if msg.kind == TxQItem.SEND_MESSAGE:
                    self._bot.send_message(*msg.args, **msg.kwargs)
                elif msg.kind == TxQItem.SEND_PHOTO:
                    self._bot.send_photo(*msg.args, **msg.kwargs)
                elif msg.kind == TxQItem.SEND_POLL:
                    self._bot.send_poll(*msg.args, **msg.kwargs)
                elif msg.kind == TxQItem.SEND_STICKER:
                    self._bot.send_sticker(*msg.args, **msg.kwargs)
                elif msg.kind == TxQItem.ANSWER_CALLBACK_QUERY:
                    self._bot.answer_callback_query(*msg.args, **msg.kwargs)
                elif msg.kind == TxQItem.ANSWER_INLINE_QUERY:
                    self._bot.answerInlineQuery(*msg.args, **msg.kwargs)
                else:
                    raise NotImplementedError

            if self._exit_lock.acquire(blocking=False):
                break

        logger.info('Stopping {}:_tx_thread'.format(type(self).__name__))
