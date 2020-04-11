''' manage instance creation/destruction '''
import logging

from misc import StoppableThread
from queue import Empty
from threading import Thread
from multiprocessing import Queue
from instance import Instance
from master_instance import MasterInstance
from pb_cfg import LOGGER_NAME


logger = logging.getLogger(LOGGER_NAME)


class InstanceManager(StoppableThread):
    ''' manage instance creation/destruction '''

    def __init__(self, max_instances=10):
        super().__init__()

        self._active_instances = [None for x in range(max_instances)]

        self._pending_jobs = Queue()

        self._master_instance = MasterInstance("Master Instance")

    def create_instance(self, kind: Instance, created_callback=None, **kwargs):
        ''' 
            push new item into pending job queue 
            kind        -> class of the instance
            kwargs      -> arguments that will be passed to the kind constructor
            callback    -> function to call when the instance has been created
        '''
        op = {'op': 'CREATE', 'ARGS': (kind, created_callback, kwargs)}
        self._pending_jobs.put(op)

    def destroy_instance(self, inst_id, destroyed_callback=None):
        '''
            push new item into pending job queue
            inst_id     -> id of the instance to stop
            callback    -> function to call when the instance has been created
        '''
        op = {'op': 'DESTROY', 'ARGS': (inst_id, destroyed_callback)}
        self._pending_jobs.put(op)

    def start(self):
        super().start()
        self._master_instance.start()

    def _run(self):
        while True:

            # If we should stop, stop all child processes first
            if self.should_stop():
                self._stop_all_instances()
                break

            try:
                item = self._pending_jobs.get(timeout=1)
            except Empty:
                continue

            if item and 'CREATE' in item:
                kind, callback, kwargs = item['ARGS']
                inst_id = self._create_instance(kind, **kwargs)

                # Do the callback
                # TODO not sure if this will work since garbage collection maybe kills the thread ??
                Thread(target=callback, args=(inst_id)).start()

            elif item and 'DESTROY' in item:
                inst_id, callback = item['ARGS']
                self._destroy_instance(inst_id)

                # Do the callback
                # TODO not sure if this will work since garbage collection maybe kills the thread ??
                Thread(target=callback).start()
            else:
                logger.error(
                    'Queue item with incorrect format {}'.format(item))

    def _create_instance(self, kind: Instance, **kwargs):
        ''' 
            Create an instance of type kind 
            Returns the instance id of new instance
            None if could not create    
        '''

        empty_slot = self.get_next_free_instance_slot()

        if empty_slot is None:
            logger.info(
                'Could not create instance since all instance slots are full')
            return None

        try:
            # Create new instance
            self._active_instances[empty_slot] = kind(
                empty_slot, **kwargs)
        except Exception as ex:
            logger.error('Failed to create instance of {} because of {}'.format(
                type(kind).__name__, ex))
            self._active_instances[empty_slot] = None
            return None

        return empty_slot

    def _destroy_instance(self, inst_id):

        inst = self._active_instances[inst_id]

        if not inst.stop():
            logger.error(
                'Failed to gracefully stop instance {}'.format(inst_id))
            logger.error(
                'Attempting to kill process {}'.format(inst.get_name()))

            inst.terminate()

    def _stop_all_instances(self):
        ''' attempt to stop all instances '''

        logger.info('Stopping master instance ...'.format())
        if not self._master_instance.stop():
            logger.error('Failed to gracefully master instance')
            logger.error('Attempting to kill it')
            self._master_instance.terminate()

        for (idx, inst) in enumerate(self._active_instances):
            if inst:
                logger.info('Stopping instance {} ...'.format(idx))
                # TODO inst.save_state()
                self._destroy_instance(idx)
                inst = None

    def send_to_master_instance(self, msg):
        ''' getter for master instance '''
        return self._master_instance.input_msg_q.put(msg)

    def get_next_free_instance_slot(self):
        ''' Find the next available instance slot '''
        for idx, content in enumerate(self._active_instances):
            if not content:
                return idx

        return None

    def chat_id_to_instance_id(self, chat_id):
        ''' given a chat id find the matching instance id '''

        matches = []
        for inst in self._active_instances[:]:
            if inst and chat_id in inst.find_by['CHAT_ID']:
                matches += inst.id_

        return matches

    def user_id_to_instance_id(self, user_id):
        ''' given a user id find the matching instance id '''

        matches = []
        for inst in self._active_instances[:]:
            if inst and user_id in inst.find_by['USER_ID']:
                matches += inst.id_

        return matches

    def game_code_to_instance_id(self, game_code):
        ''' given a game code find the matching instance id '''

        matches = []
        for inst in self._active_instances[:]:
            if inst and game_code == inst.find_by['GAME_CODE']:
                matches += inst.id_

        return matches

    def get(self, inst_id):
        return self._active_instances[inst_id]


instanceManager = InstanceManager()

if __name__ == '__main__':
    logger.setLevel(level=logging.DEBUG)
    console_log = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(lineno)4d:%(filename)s(%(process)d) - %(message)s')
    console_log.setFormatter(formatter)
    logger.addHandler(console_log)
