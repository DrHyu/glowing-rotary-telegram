''' route messages from/to telegram abstraction layer from/to game instances '''
import logging

from multiprocessing import Queue
from queues import OUTBOUND_MSG_QUEUE, INBOUND_MSG_QUEUE
from misc import StoppableProcess

from pb_cfg import LOGGER_NAME
logger = logging.getLogger(LOGGER_NAME)


class Instance(StoppableProcess):

    def __init__(self, id_,):
        super().__init__()

        self.id_ = id_

        self.find_by = {
            'CHAT_ID': [],
            'USER_ID': [],
            'GAME_CODE': None
        }

        # Q where the router will put the messages belonging to this instance
        self.input_msg_q = Queue()
        # Q where outbound messages should be put
        self.inbound_msq_q = INBOUND_MSG_QUEUE
        # Q where inbound/internal messages should be put
        self.outbound_msq_q = OUTBOUND_MSG_QUEUE

    def _run(self):
        pass


def main():
    pass


if __name__ == '__main__':
    logger.setLevel(level=logging.DEBUG)
    console_log = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(lineno)4d:%(filename)s(%(process)d) - %(message)s')
    console_log.setFormatter(formatter)
    logger.addHandler(console_log)
    main()
