from abc import abstractmethod

from astra import fields
from astra import validators


class Model(object):
    """
    Parent class for all user-objects to be managed
    class Stream(models.Model):
        name = models.CharHash(max_length=128)
        ...

        def get_db(self):
            return strict_redis_instance(..)
    """

    def __init__(self, pk=None, **kwargs):
        self._astra_fields = dict()
        self._astra_hash = {}  # Hash-object cache
        self._astra_hash_loaded = False
        self._astra_fields_loaded = False
        self._astra_database = None
        self._astra_prefix = 'astra'
        self._astra_hash_exist = None

        if pk is None:
            raise ValueError('You\'re must pass pk for object')
        self.pk = str(pk)  # Always convert to str for key-safe ops.

        # When object initialize with parameters, for example
        # user1 = UserObject(1, name='Username'), then load fields from/to db
        # immediate. When object initialized as user2 = UserObject(1), then
        # information from database not obtain before first data handling
        if kwargs:
            self._astra_load_fields(**kwargs)

    @abstractmethod
    def get_db(self):
        pass

    @abstractmethod
    def save(self, action, attr=None, value=None):
        pass

    def _astra_get_db(self):
        if not self._astra_database:
            self._astra_database = self.get_db()
        return self._astra_database

    def _astra_load_fields(self, **kwargs):
        self._astra_fields_loaded = True

        for k in dir(self.__class__):  # vars() ignores parent variables
            v = getattr(self.__class__, k)
            if isinstance(v, fields.ModelField):
                new_instance_of_field = v.__class__(instance=True, model=self,
                                                    name=k, **v._options)
                self._astra_fields[k] = new_instance_of_field

        # Assign kwargs values when object will be initialized
        keys = [k for k in kwargs.keys() if k in self._astra_fields.keys()]
        initial_data = {}
        for k in keys:
            initial_data[k] = kwargs.get(k)
            self._astra_fields[k]._assign(kwargs.get(k), suppress_signal=True)
        keys and self.save(action='post_init', value=initial_data)

    def __setattr__(self, key, value):
        if key.startswith('_astra_') or key == 'pk':
            return super(Model, self).__setattr__(key, value)

        if key in self._astra_fields.keys():
            field = self._astra_fields[key]  # self.__class__.__dict__.get(key)
            field._assign(value)
        else:
            return super(Model, self).__setattr__(key, value)

    def __getattribute__(self, key):
        # When someone request _astra_fields, then start lazy loading...
        if key == '_astra_fields' and not self._astra_fields_loaded:
            self._astra_load_fields()

        # Keys + some internal methods
        if key.startswith('_astra_') or key == '__class__':
            return object.__getattribute__(self, key)

        if key in self._astra_fields:
            field = self._astra_fields[key]
            return field._obtain()

        # If key is not in the fields, we're attempt call helper
        # Ex. "user.login_strlen" call redis "strlen" method on "login" field
        key_elements = key.split('_', )
        method_name = key_elements.pop()
        field_name = '_'.join(key_elements)
        if field_name in self._astra_fields:
            field = self._astra_fields[field_name]
            return field._helper(method_name)

        # Otherwise, default behavior:
        return object.__getattribute__(self, key)

    def __dir__(self):  # TODO: Check it
        return self._astra_fields

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
        self.save(action='pre_remove', attr='pk', value=self.pk)

        # Remove all fields and one time delete entire hash
        is_hash_deleted = False
        for field in self._astra_fields.values():
            if isinstance(field, fields.BaseHash):
                if not is_hash_deleted:
                    is_hash_deleted = True
                    self._astra_get_db().delete(field._get_key_name(True))
            else:
                field._remove()
        self._astra_hash_exist = False
        self.save(action='post_remove', attr='pk', value=self.pk)

    def hash_exist(self):
        if self._astra_hash_exist is None:
            parent_class_name = self.__class__.__name__.lower()
            items = [self._astra_prefix, parent_class_name,
                     'hash', str(self.pk)]
            hash_key = '::'.join(items)
            self._astra_hash_exist = self._astra_get_db().exists(hash_key)
        return self._astra_hash_exist


class CharField(validators.CharValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'append', 'bitcount',
                               'getbit', 'getrange', 'setbit', 'setrange',
                               'strlen', 'expire', 'ttl')


class BooleanField(validators.BooleanValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'expire', 'ttl',)


class IntegerField(validators.IntegerValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'incr', 'incrby', 'decr',
                               'decrby', 'getset', 'expire', 'ttl',)


class ForeignKey(validators.ForeignObjectValidatorMixin, fields.BaseField):
    def _assign(self, value, suppress_signal=False):
        """
        Support remove hash field if None passed as value
        """
        if isinstance(value, Model):
            super(ForeignKey, self)._assign(value.pk, True)
            signal = dict(attr=self._name, action='m2m_link', value=value)
        elif value is None:
            self._model._astra_get_db().delete(self._get_key_name())
            signal = dict(attr=self._name, action='m2m_remove')
        else:
            super(ForeignKey, self)._assign(value, True)
            signal = dict(attr=self._name, action='m2m_link', value=value)

        not suppress_signal and self._model.save(**signal)

    def _obtain(self):
        """
        Convert saved pk to target object
        """
        if not self._to:
            raise RuntimeError('Relation model is not loaded')
        value = super(ForeignKey, self)._obtain()
        return self._to_wrapper(value)


class DateField(validators.DateValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'expire', 'ttl',)


class DateTimeField(validators.DateTimeValidatorMixin, fields.BaseField):
    _directly_redis_helpers = ('setex', 'setnx', 'expire', 'ttl',)


class EnumField(validators.EnumValidatorMixin, fields.BaseField):
    pass


# Hashes
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
