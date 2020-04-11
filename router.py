''' route messages from/to telegram abstraction layer from/to game instances '''
import logging

import queue

from queues import INBOUND_MSG_QUEUE, RxQItem
from misc import StoppableThread
from master_instance import MasterInstance

from pb_cfg import LOGGER_NAME
logger = logging.getLogger(LOGGER_NAME)


class Router(StoppableThread):
    ''' route messages from/to telegram abstraction layer from/to game instances '''

    COULD_NOT_ROUTE = 0
    TGT_INSTANCE_NOT_ACTIVE = 1
    MULTIPLE_TGT_INSTANCES = 2
    COULD_ROUTE = 3

    def __init__(self, instance_manager):
        super().__init__()

        self.IM = instance_manager

    def _run(self):

        while True:

            next_message = None
            try:
                # Give a timeout so thread can be stopped if left with an empty q
                next_message = INBOUND_MSG_QUEUE.get(timeout=1)
            except queue.Empty:
                pass

            if next_message:
                result, inst_id = self._route_rx_message(next_message)
                if result == self.COULD_ROUTE:
                    self._dispatch_message(inst_id, next_message)

                elif next_message.delivery_attempts > 10:
                    # Message has been attempted to re-deliver more than 10 times
                    # Seems there is some problem, to be safe for now, discard the message
                    pass

                elif result == self.TGT_INSTANCE_NOT_ACTIVE:
                    # TODO Call instance manager to try to wake up
                    next_message.delivery_attempts += 1
                    # Put item at the end of the queue
                    INBOUND_MSG_QUEUE.put(next_message)
                elif result == self.MULTIPLE_TGT_INSTANCES:
                    # TODO Call the game manager to resolve the issue
                    next_message.delivery_attempts += 1
                    # Put item at the end of the queue
                    INBOUND_MSG_QUEUE.put(next_message)
                elif result == self.COULD_NOT_ROUTE:
                    # New 'user'
                    next_message.delivery_attempts += 1
                    msg = {'task': MasterInstance.TASK_GREET_NEW_USER,
                           'args': [next_message]}
                    self.IM.send_to_master_instance(msg)

            if self.should_stop():
                break

    def _route_rx_message(self, msg):
        ''' route an inbound msg '''

        by_game_code = []
        by_chat_id = []
        by_user_id = []

        # Shoule we route by GROUP
        if bool(msg.route_by & RxQItem.ROUTE_BY_GAME_CODE):
            by_game_code = self.IM.game_code_to_instance_id(
                msg.game_code)
            if len(by_game_code) == 1:
                return self.COULD_ROUTE, by_game_code[0]
        if bool(msg.route_by & RxQItem.ROUTE_BY_CHAT_ID):
            by_chat_id = self.IM.game_code_to_instance_id(
                msg.chat_id)
            if len(by_chat_id) == 1:
                return self.COULD_ROUTE, by_chat_id[0]
        if bool(msg.route_by & RxQItem.ROUTE_BY_USER_ID):
            by_user_id = self.IM.game_code_to_instance_id(
                msg.chat_id)
            if len(by_user_id) == 1:
                return self.COULD_ROUTE, by_user_id[0]

        # User/Chat/Game not registered in any instance
        if not by_game_code and not by_chat_id and not by_user_id:
            return self.COULD_NOT_ROUTE, None
        # There was not a conclusive match
        else:
            return self.MULTIPLE_TGT_INSTANCES, by_game_code + by_chat_id + by_user_id

    def _dispatch_message(self, instance_id, msg):
        return self.IM.get(instance_id).input_msg_q.put(msg)
