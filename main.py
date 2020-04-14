''' entry point for the whole thing .... '''


import logging
import time

import coloredlogs

from queues import INBOUND_MSG_QUEUE, OUTBOUND_MSG_QUEUE
from telegram_abstraction_layer import TelegramAbstractionLayer
from instance_manager import InstanceManager
from router import Router


from pb_cfg import LOGGER_NAME
from pvt_cfg import TELEGRAM_API_TOKEN


logger = logging.getLogger(LOGGER_NAME)


def main():

    if INBOUND_MSG_QUEUE is None or OUTBOUND_MSG_QUEUE is None:
        raise "Queues not running"

    # Start the telegram abstraction layer
    tal = TelegramAbstractionLayer(TELEGRAM_API_TOKEN)
    tal.start()

    # Start the instance manager
    im = InstanceManager()
    im.start()

    # Start the router
    rtr = Router(im)
    rtr.start()

    try:
        while True:
            time.sleep(1)
    finally:
        rtr.stop()
        im.stop()
        tal.stop()


if __name__ == '__main__':
    # logger.setLevel(level=logging.DEBUG)
    # console_log = logging.StreamHandler()
    # formatter = logging.Formatter(
    #     '%(asctime)s %(levelname)s %(lineno)d:%(filename)s(%(process)d) - %(message)s')

    coloredlogs.install(level='DEBUG', logger=logger,
                        fmt='%(asctime)s %(levelname)-5s %(lineno)-4d:%(filename)-30s - %(message)s')

    # console_log.setFormatter(formatter)
    # logger.addHandler(console_log)
    main()
