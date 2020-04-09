''' Abstraction layer for the telegram api '''

import time
import logging
from threading import Lock, Thread

from telegram import Bot
from telegram.ext import Updater, CallbackQueryHandler, MessageHandler
from telegram.ext.filters import Filters

from pb_cfg import LOGGER_NAME
from pvt_cfg import TELEGRAM_API_TOKEN
from queues import RxMessageQ, TxMessageQ, RxMessageQItem, TxMessageQItem


logger = logging.getLogger(LOGGER_NAME)


class TelegramAbstractionLayer():
    ''' I/O with telegram server '''

    def __init__(self, api_key, auto_start=True):

        self._exit_lock = Lock()

        self._api_key = api_key
        # 'Bot' telegram instance
        self._bot = None
        self._tx_thread = None
        # 'Updater' telegram instance
        self._rx_thread = None

        # Trafic coming from the user is divided in three queues
        self.rx_q = RxMessageQ()

        # Ouput trafic in a single queue
        self.tx_q = TxMessageQ()

        if auto_start:
            self.start()

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

        self.rx_q.put(RxMessageQItem(
            RxMessageQItem.TEXT_MSG, args=[update, context]))

    def command_handler(self, update, context):
        ''' forward command messages '''
        logger.debug('CMD {}: {}'.format(
            update.message.message_id, update.message.text))
        self.rx_q.put(RxMessageQItem(
            RxMessageQItem.COMMAND_MSG, args=[update, context]))

    def callback_query_handler(self, update, context):
        ''' forward callback messages '''
        logger.debug('CBK QRY {}: {}'.format(
            update.message.message_id, update.message.text))
        self.rx_q.put(RxMessageQItem(
            RxMessageQItem.CALLBACK_QUERY_MSG, args=[update, context]))

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
            if not self.tx_q.empty():
                msg = self.tx_q.get()

                if msg.kind == TxMessageQItem.SEND_MESSAGE:
                    self._bot.send_message(*msg.args, **msg.kwargs)
                elif msg.kind == TxMessageQItem.SEND_PHOTO:
                    self._bot.send_photo(*msg.args, **msg.kwargs)
                elif msg.kind == TxMessageQItem.SEND_POLL:
                    self._bot.send_poll(*msg.args, **msg.kwargs)
                elif msg.kind == TxMessageQItem.SEND_STICKER:
                    self._bot.send_sticker(*msg.args, **msg.kwargs)
                elif msg.kind == TxMessageQItem.ANSWER_CALLBACK_QUERY:
                    self._bot.answer_callback_query(*msg.args, **msg.kwargs)
                elif msg.kind == TxMessageQItem.ANSWER_INLINE_QUERY:
                    self._bot.answerInlineQuery(*msg.args, **msg.kwargs)
                else:
                    raise NotImplementedError

            if self._exit_lock.acquire(blocking=False):
                break

        logger.info('Stopping {}:_tx_thread'.format(type(self).__name__))


if __name__ == '__main__':
    logger.setLevel(level=logging.DEBUG)
    console_log = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(lineno)4d:%(filename)s(%(process)d) - %(message)s')
    console_log.setFormatter(formatter)
    logger.addHandler(console_log)

    tal = TelegramAbstractionLayer(TELEGRAM_API_TOKEN)

    try:
        while True:
            time.sleep(1)
    finally:
        tal.stop()
