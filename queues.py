''' All queues items with 'enums' '''

from queue import Queue


class RxMessageQItem():
    ''' item in the rx message queue to be passed to the filter '''
    TEXT_MSG = 0
    COMMAND_MSG = 1
    CALLBACK_QUERY_MSG = 2

    def __init__(self, kind, args=None, kwargs=None):

        self.kind = kind
        self.args = args if args else []
        self.kwargs = kwargs if kwargs else {}


class RxMessageQ(Queue):
    '''type check put func'''

    def put(self, item: RxMessageQItem, *args, **kwargs):
        super().put(item, *args, **kwargs)


class TxMessageQItem():
    ''' item in the tx message q to be outputed by the bot'''
    SEND_MESSAGE = 0
    SEND_PHOTO = 1
    SEND_POLL = 2
    SEND_STICKER = 3
    ANSWER_CALLBACK_QUERY = 4
    ANSWER_INLINE_QUERY = 5

    def __init__(self, kind, args=None, kwargs=None):

        self.kind = kind
        self.args = args if args else []
        self.kwargs = kwargs if kwargs else {}


class TxMessageQ(Queue):
    '''type check put func'''

    def put(self, item: TxMessageQItem, *args, **kwargs):
        super().put(item, *args, **kwargs)
