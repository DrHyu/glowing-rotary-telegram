''' master instance '''

import logging

from queue import Empty
from queues import RxQItem, TxQItem
from instance import Instance
from pb_cfg import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class MasterInstance(Instance):
    '''
        Master Instance
        All trafic for which there is no target will be redirected here.
        All trafic for which the target isntance is not active will be redirected here
        In charge of triggering the creation/destruction of other instances.

    '''
    TASK_GREET_NEW_USER = 0
    TASK_CREATE_NEW_INSTANCE = 1

    def _run(self):
        while True:

            if self.should_stop():
                break

            try:
                task = self.input_msg_q.get(timeout=1)
            except Empty:
                continue

            if task['task'] == self.TASK_GREET_NEW_USER:
                self._greet_new_user(*task['args'])
            elif task['task'] == self.TASK_CREATE_NEW_INSTANCE:
                pass

    def _greet_new_user(self, msg: RxQItem):
        logger.debug('Got message'.format())
        chat_id = msg.args[0].message.chat_id

        repply = TxQItem(TxQItem.SEND_MESSAGE, args=(
            chat_id, "Helo ! I be de MASTER INSTANCE !!!"))
        self.outbound_msq_q.put(repply)
