# All model fields inherited from this
from astra.validators import ForeignObjectValidatorMixin


class ModelField(object):
    directly_redis_helpers = ()  # Direct method helpers
    field_type_name = '--'

    def __init__(self, **kwargs):
        if 'instance' in kwargs:
            self.name = kwargs['name']
            self.model = kwargs['model']
            self.db = kwargs['db']
        self.options = kwargs

    def get_key_name(self, is_hash=False):
        """
        Create redis key. Schema:
        prefix::object_name::field_type::id::field_name, e.g.
            prefix::user::fld::12::login
            prefix::user::list::12::sites
            prefix::user::zset::12::winners
            prefix::user::hash::54
        """
        parent_class_name = self.model.__class__.__name__.lower()
        items = [self.model._astra_prefix, parent_class_name,
                 self.field_type_name, str(self.model.pk)]
        if not is_hash:
            items.append(self.name)
        return '::'.join(items)

    def assign(self, value):
        raise NotImplementedError('Subclasses must implement assign')

    def obtain(self):
        raise NotImplementedError('Subclasses must implement obtain')

    def get_helper_func(self, method_name):
        if method_name not in self.directly_redis_helpers:
            raise AttributeError('Invalid attribute with name "%s"'
                                 % (method_name,))
        original_command = getattr(self.db, method_name)
        current_key = self.get_key_name()

        def _method_wrapper(*args, **kwargs):
            new_args = [current_key]
            for v in args:
                new_args.append(v)
            return original_command(*new_args, **kwargs)

        return _method_wrapper

    def remove(self):
        self.db.delete(self.get_key_name())


# Fields:
class BaseField(ModelField):
    field_type_name = 'fld'

    def assign(self, value):
        saved_value = self._convert_set(value)
        self.db.set(self.get_key_name(), saved_value)

    def obtain(self):
        value = self.db.get(self.get_key_name())
        return self._convert_get(value)

    def _convert_set(self, value):
        """ Check saved value before send to server """
        raise NotImplementedError('Subclasses must implement _convert_set')

    def _convert_get(self, value):
        """ Convert server answer to user type """
        raise NotImplementedError('Subclasses must implement _convert_get')


# Hashes
class BaseHash(ModelField):
    field_type_name = 'hash'

    def assign(self, value):
        saved_value = self._convert_set(value)
        self.db.hset(self.get_key_name(True), self.name, saved_value)
        if self.model._astra_hash_loaded:
            self.model._astra_hash[self.name] = saved_value
        self.model._astra_hash_exist = True

    def obtain(self):
        self._load_hash()
        return self._convert_get(self.model._astra_hash.get(self.name, None))

    def _load_hash(self):
        if self.model._astra_hash_loaded:
            return
        self.model._astra_hash_loaded = True
        self.model._astra_hash = \
            self.db.hgetall(
                self.get_key_name(True))
        if not self.model._astra_hash:  # None if hash field is not exist
            self.model._astra_hash = {}
            self.model._astra_hash_exist = False
        else:
            self.model._astra_hash_exist = True

    def _convert_set(self, value):
        """ Check saved value before send to server """
        raise NotImplementedError('Subclasses must implement _convert_set')

    def _convert_get(self, value):
        """ Convert server answer to user type """
        raise NotImplementedError('Subclasses must implement _convert_get')

    def remove(self):
        # Delete one record on hash. _astra_hash_exist is not changes
        # eg hash may be exist
        self.db.hdel(self.get_key_name(True), self.name)

    def force_hash_exists(self):
        self.model._astra_hash_exist = self.db.exists(self.get_key_name(True))


# Implements for three types of lists
class BaseCollection(ForeignObjectValidatorMixin, ModelField):
    field_type_name = ''
    _allowed_redis_methods = ()
    _single_object_answered_redis_methods = ()
    _list_answered_redis_methods = ()
    # Other methods will be answered directly

    def obtain(self):
        return self  # for delegate to __getattr__ on this class

    def assign(self, value):
        if value is None:
            self.remove()
        else:
            raise ValueError('Collections fields is not possible '
                             'assign directly')

    def __getattr__(self, item):
        if item not in self._allowed_redis_methods:
            return super(BaseCollection, self).__getattribute__(item)

        original_command = getattr(self.db, item)
        current_key = self.get_key_name()

        def _method_wrapper(*args, **kwargs):
            from astra import models

            # Scan passed args and convert to pk if passed models
            new_args = [current_key]
            new_kwargs = dict()
            for v in args:
                new_args.append(v.pk if isinstance(v, models.Model) else v)
            for k, v in kwargs.items():
                new_kwargs[k] = v.pk if isinstance(v, models.Model) else v

            # Call original method on the database
            answer = original_command(*new_args, **new_kwargs)

            # Wrap to model
            if item in self._single_object_answered_redis_methods:
                return None if not answer else self._to(answer)

            if item in self._list_answered_redis_methods:
                wrapper_answer = []
                for pk in answer:
                    if not pk:
                        wrapper_answer.append(None)
                    else:
                        if isinstance(pk, tuple) and len(pk) > 0:
                            wrapper_answer.append((self._to(pk[0]), pk[1]))
                        else:
                            wrapper_answer.append(self._to(pk))

                return wrapper_answer
            return answer  # Direct answer

        return _method_wrapper
