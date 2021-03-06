''' All queues items with 'enums' '''
import logging

from multiprocessing import Queue
import multiprocessing as mp
import multiprocessing.queues as mpq

from pb_cfg import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)


class RxQItem():
    ''' item in the rx message queue to be passed to the filter '''
    TEXT_MSG = 0
    COMMAND_MSG = 1
    CALLBACK_QUERY_MSG = 2

    # How should this Item be routed
    # Several options can be or'ed together
    ROUTE_BY_CHAT_ID = 1
    ROUTE_BY_USER_ID = 2
    ROUTE_BY_GAME_CODE = 4

    def __init__(self, kind, route_by=ROUTE_BY_CHAT_ID, chat_id=None, user_id=None, game_code=None, args=None, kwargs=None):
        '''
            kind        -> TEXT_MSG or COMMAND_MSG or CALLBACK_QUERY_MSG
            route_by    -> What ID should be used to route this item.
                            Several options can be or'ed together.
                            The router will search in this order if more than one flag is set.
                            ROUTE_BY_GAME_CODE -> ROUTE_BY_CHAT_ID -> ROUTE_BY_USER_ID
            chat_id     -> chat id to match in Instance to assign this message
            user_id     -> user id to match in Instance to assign this message
            game_code   -> game code to match in Instance to assign this message
            args        -> 'payload' of the message in a list
            kwargs      -> 'payload' of the message in a dict
        '''
        self.route_by = route_by
        self.chat_id = chat_id
        self.user_id = user_id
        self.game_code = game_code

        self.kind = kind
        self.args = args if args else []
        self.kwargs = kwargs if kwargs else {}

        self.delivery_attempts = 0

    def __str__(self):

        out_str = 'Game Code: {} '.format(self.game_code)
        out_str += 'Chat ID: {} '.format(self.chat_id)
        out_str += 'User ID: {}'.format(self.user_id)

        if 'update' in self.kwargs and self.kwargs['update'].message:
            out_str += ' Message: {}'.format(
                self.kwargs['update'].message.text)

        return out_str

    def __repr__(self):
        return self.__str__()


# class RxMessageQ(queue.Queue):
#     '''type check put func'''

#     def put(self, item: RxQItem, *args, **kwargs):
#         super().put(item, *args, **kwargs)


class TxQItem():
    ''' item in the tx message q to be outputed by the bot'''

    def __init__(self, func_call=None, args=None, kwargs=None):

        if func_call is None:
            logger.error('TxQItem must have a function to call in the Bot')

        self.func_call = func_call
        self.args = args if args else []
        self.kwargs = kwargs if kwargs else {}

    def __str__(self):
        return 'Func: {} Args: {} Kwargs: {}'.format(self.func_call, self.args, self.kwargs)

    def __repr__(self):
        return self.__str__()


class TxMessageQ(mpq.Queue):
    '''
        The idea is to call the Queue as if calling the telegram bot directly
        eg: queue_instance.send_message(chat_id, text, parse_mode=None, ...)
        The __getattr__ will catch this function calls, transform them into TxQItem and call put()
        On the other end of the Queue, the bot will take TxQItem execute the func_calls
    '''

    def __init__(self, *args, **kwargs):
        ctx = mp.get_context()
        super().__init__(*args, **kwargs, ctx=ctx)

    def __getattr__(self, attr):
        '''
            When trying to get an attribute that doesn't exist return a callable (lambda here)
            eg. user calls:
                queue_instance.send_message(chat_id, text, parse_mode=None, ...)
                The attr requested is only the 'name' of the func, so 'send_message'
            we return:
                lambda *args, **kwargs: self.put_func_call('send_message', *args, **kwargs)
            the user executes the lambda func which essentially becomes:
                queue_instance.put_func_call('send_message', chat_id, text, parse_mode=None, ...)
        '''
        return lambda *args, **kwargs: self.put_func_call(attr, *args, **kwargs)

    def put_func_call(self, func_name, *args, **kwargs):
        ''' Initialize and put() a TxQItem in the queue '''
        # logger.debug('{}{}{}'.format(func_name, args, kwargs))
        item = TxQItem(func_call=func_name, args=args, kwargs=kwargs)
        self.put(item)
        logger.debug('Put item: {}'.format(item))


# There are three 'kinds' of queues
# 1- Inbound queue:
# Anyone can put items to this queue (Instances or Updater).
# Only the router it allowed to get items from it.
# The router will then dispatch the messages to the input Q of Instances
# INBOUND_MSG_QUEUE = RxMessageQ()
INBOUND_MSG_QUEUE = Queue()

# 2- Outbound queue
# Instances can put items in this queue.
# Only the Bot is allowed to get from this queue
# The bot will attempt to send every message in the Q with only the information
# available in the Q item.
OUTBOUND_MSG_QUEUE = TxMessageQ()
# OUTBOUND_MSG_QUEUE = TxMessageQ()

# 3- Instance input queue
# Each instance will have an input queue where the router will put the corresponging
# message obtained from the INBOUND_MSG_QUEUE
# Definition is inside each Instance
