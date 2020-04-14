''' collection of miscelaneous classes '''
import logging
from abc import ABC, abstractmethod
from threading import Thread
from threading import Lock as TLock

from multiprocessing import Process
from multiprocessing import Lock as MPLock

from pb_cfg import LOGGER_NAME
logger = logging.getLogger(LOGGER_NAME)


class StoppableThread(ABC):
    ''' Abstract class with a thread that can be stopped '''

    def __init__(self):

        self._thread = None
        self._exit_lock = TLock()

    def start(self, *args, **kwargs):
        ''' start the thread '''
        logger.info('Staring {}'.format(type(self).__name__))

        if not self._exit_lock.acquire():
            logger.error('Could not start {}'.format(type(self).__name__))
            return False

        self._thread = Thread(target=self._run, args=args, kwargs=kwargs)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        ''' warm stop the thread '''

        logger.info('Stopping {}'.format(type(self).__name__))
        if not self._thread or not self._exit_lock.locked():
            logger.error('Thread for {} is not currently running !'.format(
                type(self).__name__))
            return True

        # Exit condition
        self._exit_lock.release()
        # Wait for it to join
        self._thread.join(2)

        return self._thread.is_alive()

    @abstractmethod
    def _run(self):
        '''
            To be implemented by child class
            Acquiring the self._exit_lock in the exit condition.
        '''

    def should_stop(self):
        return self._exit_lock.acquire(blocking=False)


class StoppableProcess(ABC):
    ''' Abstract class with a thread that can be stopped '''

    def __init__(self):

        self._process = None
        self._exit_lock = MPLock()

    def start(self, *args, **kwargs):
        ''' start the thread '''

        logger.info('Staring {}'.format(type(self).__name__))

        if not self._exit_lock.acquire():
            logger.error('Could not start {}'.format(type(self).__name__))
            return False

        self._process = Process(target=self._run, args=args, kwargs=kwargs)
        self._process.start()

    def stop(self):
        ''' warm stop the thread '''

        logger.info('Stopping {}'.format(type(self).__name__))
        if not self._process or self._exit_lock.acquire(block=False):
            logger.error('Process for {} is not currently running !'.format(
                type(self).__name__))
            self._exit_lock.release()
            return True

        # Exit condition
        self._exit_lock.release()
        # Wait for it to join
        self._process.join(2)

        return self._process.exitcode is not None

    def terminate(self):
        self._process.terminate()

    def get_name(self):
        return self._process.name()

    @abstractmethod
    def _run(self):
        '''
            To be implemented by child class
            Acquiring the self._exit_lock in the exit condition.
        '''

    def should_stop(self):
        return self._exit_lock.acquire(block=False)


def get_chat_id_from_update(update):

    if update.callback_query is not None:
        # Callback querry message, chat id is in callback_querry.message.chat.id
        return update.callback_query.message.chat.id
    elif update.message is not None:
        return update.message.chat.id
    else:
        return None
