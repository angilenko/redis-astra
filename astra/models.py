import redis

from astra import fields
from astra import signals
from astra import validators


class Model(object):
    """
    Parent class for all user-objects to be managed
    class Stream(models.Model):
        database = strict_redis_instance(..)
        name = models.CharHash(max_length=128)
        ...
    """

    prefix = 'astra'

    def __init__(self, pk=None, **kwargs):
        self._fields = dict()
        self._helpers = set()
        self._hash = {}  # Hash-object cache
        self._hash_loaded = False
        assert isinstance(self.database, redis.StrictRedis)

        if not pk:
            raise ValueError('You\'re must pass pk for object')
        self.pk = str(pk)  # Always convert to str for key-safe ops.

        for k in dir(self.__class__):  # vars() ignores parent variables
            v = getattr(self.__class__, k)
            if isinstance(v, fields.ModelField):
                new_instance_of_field = v.__class__(instance=True, model=self,
                                                    name=k, **v._options)
                self._fields[k] = new_instance_of_field

        # Assign kwargs values when object will be initialized
        keys = [k for k in kwargs.keys() if k in self._fields.keys()]
        for k in keys:
            self._fields[k]._assign(kwargs.get(k), suppress_signal=True)
        keys and signals.post_init.send(sender=self.__class__, instance=self)

    def __setattr__(self, key, value):
        if hasattr(self, '_fields') and key in self._fields.keys():
            field = self._fields[key]  # self.__class__.__dict__.get(key)
            field._assign(value)
        else:
            return super(Model, self).__setattr__(key, value)

    def __getattribute__(self, key):
        internal_keys = ('_fields', 'database', '__class__', 'prefix',
                         '_hash_loaded')
        if key in internal_keys:
            return object.__getattribute__(self, key)

        if key in self._fields:
            field = self._fields[key]
            return field._obtain()

        # If key is not in the fields, we're attempt call helper
        # Ex. "user.login_strlen" call redis "strlen" method on "login" field
        key_elements = key.split('_', )
        method_name = key_elements.pop()
        field_name = '_'.join(key_elements)
        if field_name in self._fields:
            field = self._fields[field_name]
            return field._helper(method_name)

        # Otherwise, default behavior:
        return object.__getattribute__(self, key)

    def __dir__(self):  # TODO: Check it
        return self._fields

    def __eq__(self, other):
        """
        Compare two models
        More magic is here: http://www.rafekettler.com/magicmethods.html
        """
        if isinstance(other, Model):
            return self.pk == other.pk
        return super(Model, self).__eq__(other)

    def __repr__(self):
        return '<Model %s(pk=%s)>' % (self.__class__.__name__, self.pk)

    def remove(self):
        signals.pre_remove.send(sender=self.__class__, instance=self)

        # Remove all fields and one time delete entire hash
        is_hash_deleted = False
        for field in self._fields.values():
            if isinstance(field, fields.BaseHash):
                if not is_hash_deleted:
                    is_hash_deleted = True
                    self.database.delete(field._get_key_name(True))
            else:
                field._remove()
        signals.post_remove.send(sender=self.__class__)


class CharField(validators.CharValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'append', 'bitcount',
                               'getbit', 'getrange', 'setbit', 'setrange',
                               'strlen',)


class BooleanField(validators.BooleanValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx',)


class IntegerField(validators.IntegerValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'incr', 'incrby', 'decr',
                               'decrby', 'getset',)


class ForeignKey(validators.ForeignObjectValidatorMixin, fields.BaseField):
    def _assign(self, value, suppress_signal=False):
        """
        Support remove hash field if None passed as value
        """
        if isinstance(value, Model):
            super(ForeignKey, self)._assign(value.pk)
            signal = dict(sender=self._model.__class__, instance=self._model,
                          attr=self._name, action='link', value=value)
        elif value is None:
            self._model.database.delete(self._get_key_name())
            signal = dict(sender=self._model.__class__, instance=self._model,
                          attr=self._name, action='delete', value=None)
        else:
            super(ForeignKey, self)._assign(value)
            signal = dict(sender=self._model.__class__, instance=self._model,
                          attr=self._name, action='link', value=value)

        not suppress_signal and signals.m2m_changed.send(**signal)

    def _obtain(self):
        """
        Convert saved pk to target object
        """
        if not self._to:
            raise RuntimeError('Relation model is not loaded')
        value = super(ForeignKey, self)._obtain()
        return None if value is None else self._to(value)


class DateField(validators.DateValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx',)


class DateTimeField(validators.DateTimeValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx',)


class EnumField(validators.EnumValidatorMixin, fields.BaseField):
    pass




class CharHash(validators.CharValidatorMixin, fields.BaseHash):
    pass


class BooleanHash(validators.BooleanValidatorMixin, fields.BaseHash):
    pass


class IntegerHash(validators.IntegerValidatorMixin, fields.BaseHash):
    pass


class DateHash(validators.DateValidatorMixin, fields.BaseHash):
    pass


class DateTimeHash(validators.DateTimeValidatorMixin, fields.BaseHash):
    pass


class EnumHash(validators.EnumValidatorMixin, fields.BaseHash):
    pass


class ForeignKeyHash(validators.ForeignObjectValidatorMixin, fields.BaseHash):
    def _assign(self, value, suppress_signal=False):
        """
        Support remove hash field if None passed as value
        """
        if isinstance(value, Model):
            super(ForeignKeyHash, self)._assign(value.pk)
            signal = dict(sender=self._model.__class__, instance=self._model,
                          attr=self._name, action='link', value=value)
        elif value is None:
            self._model.database.hdel(self._get_key_name(True), self._name)
            if self._model._hash_loaded:
                del self._model._hash[self._name]
            signal = dict(sender=self._model.__class__, instance=self._model,
                          attr=self._name, action='delete', value=None)
        else:
            super(ForeignKeyHash, self)._assign(value)
            signal = dict(sender=self._model.__class__, instance=self._model,
                          attr=self._name, action='link', value=value)

        not suppress_signal and signals.m2m_changed.send(**signal)

    def _obtain(self):
        """
        Convert saved pk to target object
        """
        if not self._to:
            raise RuntimeError('Relation model is not loaded')
        value = super(ForeignKeyHash, self)._obtain()
        return None if value is None else self._to(value)


class List(fields.BaseCollection):
    """
    :
    """
    _field_type_name = 'list'

    _allowed_redis_methods = ('lindex', 'linsert', 'llen', 'lpop', 'lpush',
                              'lpushx', 'lrange', 'lrem', 'lset', 'ltrim',
                              'rpop', 'rpoplpush', 'rpush', 'rpushx',)
    _single_object_answered_redis_methods = ('lindex', 'lpop', 'rpop',)
    _list_answered_redis_methods = ('lrange',)

    def __len__(self):
        return self.llen()

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self.lrange(item.start, item.stop)
        else:
            ret = self.lrange(item, item)
            return ret[0] if len(ret) == 1 else None


class Set(fields.BaseCollection):
    _field_type_name = 'set'
    _allowed_redis_methods = ('sadd', 'scard', 'sdiff', 'sdiffstore', 'sinter',
                              'sinterstore', 'sismember', 'smembers', 'smove',
                              'spop', 'srandmember', 'srem', 'sscan', 'sunion',
                              'sunionstore')
    _single_object_answered_redis_methods = ('spop',)
    _list_answered_redis_methods = ('sdiff', 'sinter', 'smembers',
                                    'srandmember', 'sscan', 'sunion',)

    def __len__(self):
        return self.scard()


class SortedSet(fields.BaseCollection):
    _field_type_name = 'zset'
    _allowed_redis_methods = ('zadd', 'zcard', 'zcount', 'zincrby',
                              'zinterstore', 'zlexcount', 'zrange',
                              'zrangebylex', 'zrangebyscore', 'zrank', 'zrem',
                              'zremrangebylex', 'zremrangebyrank',
                              'zremrangebyscore', 'zrevrange',
                              'zrevrangebylex', 'zrevrangebyscore', 'zrevrank',
                              'zscan', 'zscore', 'zunionstore')
    _single_object_answered_redis_methods = ()
    _list_answered_redis_methods = ('zrange', 'zrangebylex', 'zrangebyscore',
                                    'zrevrange', 'zrevrangebylex',
                                    'zrevrangebyscore', 'zscan', )

    def __len__(self):
        return self.zcard()

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self.zrangebyscore(item.start or '-inf',
                                      item.stop or '+inf')
        else:
            ret = self.zrangebyscore(item, item)
            return ret[0] if len(ret) == 1 else None
