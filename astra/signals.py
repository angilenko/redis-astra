from pydispatch import dispatcher
from pydispatch.dispatcher import Any, Anonymous


class ModelSignal(object):
    def __init__(self, signal=None, handler_args=None):
        super(ModelSignal, self).__init__()
        self.signal = signal or 'sig-%i' % id(self)
        self.handler_args = handler_args

    def send(self, sender=Anonymous, **kwargs):
        # params = {k: v for k, v in kwargs.items() if k in self.handler_args}
        params = {}
        for k, v in kwargs.items():
            if k in self.handler_args:
                params[k] = v
        dispatcher.send(self.signal, sender, **params)

    def connect(self, receiver, sender=Any):
        dispatcher.connect(receiver, self.signal, sender)

    def disconnect(self, receiver, sender=Any):
        dispatcher.disconnect(receiver, self.signal, sender)


# Besides handler_args receiver take signal and sender args
pre_assign = ModelSignal('pre_assign',
                         handler_args=['instance', 'attr', 'value'])
post_assign = ModelSignal('post_assign',
                          handler_args=['instance', 'attr', 'value'])

# after __init__ with params
post_init = ModelSignal('post_init', handler_args=['instance'])

pre_remove = ModelSignal('pre_remove', ['instance'])
post_remove = ModelSignal('post_remove')

# foreign keys changes:
m2m_changed = ModelSignal('m2m_changed', ['instance', 'attr', 'action',
                                          'value'])

# todo: collection manipulate signals?.. zadd, zrem?..
