''' master instance '''

import logging
import time

from queue import Empty
from queues import RxQItem, TxQItem
from instance import Instance
from session import SelectGameSession

from misc import get_chat_id_from_update

from pb_cfg import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class MasterInstance(Instance):
    '''
        Master Instance
        All trafic for which there is no target will be redirected here.
        All trafic for which the target isntance is not active will be redirected here
        In charge of triggering the creation/destruction of other instances.

    '''
    TASK_HANDLE_NEW_USER = 0
    TASK_CREATE_NEW_INSTANCE = 1

    def __init__(self, id_):
        super().__init__(id_)
        self.sessions = {}

    def _run(self):
        while True:

            if self.should_stop():
                break

            try:
                task = self.input_msg_q.get(timeout=1)
            except Empty:
                continue

            if task['task'] == self.TASK_HANDLE_NEW_USER:

                if 'msg' not in task or 'update' not in task['msg'].kwargs:
                    continue
                # Find chat ID/user ID
                update = task['msg'].kwargs['update']

                chat_id = get_chat_id_from_update(update)

                # If there is no session for this chat id start a new one
                if chat_id not in self.sessions:
                    self.sessions[chat_id] = SelectGameSession(
                        output_q=self.outbound_msq_q)

                # Pass the new message to the session
                self.sessions[chat_id].iterate(update=update)

            else:
                pass

            # Periodically check if the sessions should be deleted because of timeout
            for chat_id in list(self.sessions.keys()):
                session = self.sessions[chat_id]
                curr_time = time.time()
                if curr_time - session.alive_timestamp > session.TIMEOUT:
                    session.end_session()

                    logger.debug(
                        'Deleting timedout session for chat {}'.format(chat_id))
                    del self.sessions[chat_id]
