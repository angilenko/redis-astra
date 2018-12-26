from astra import base_fields


class Model(object):
    """
    Parent class for all user-defined objects.
    For example:

    db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)

    class Stream(models.Model):
        name = models.CharHash()
        ...

        def get_db(self):
            return db
    """

    def __init__(self, pk=None, **kwargs):
        self._astra_hash = {}  # Hash-object cache
        self._astra_hash_loaded = False
        self._astra_database = None
        self._astra_hash_exist = None

        if pk is None:
            raise ValueError('You must pass pk for new or existing object')
        self.pk = str(pk)

        self._capture_fields()
        self._make_methods()

        # Load fields:
        for k in kwargs:
            setattr(self, k, kwargs.get(k))

    def _capture_fields(self):
        # Save original fields because they will be replaced to properties
        cls = self.__class__
        if not hasattr(cls, '_astra_fields'):
            astra_fields = {}

            for k in dir(cls):  # vars() ignores parent variables
                v = getattr(self.__class__, k)
                if isinstance(v, base_fields.ModelField):
                    astra_fields[k] = v

            setattr(cls, '_astra_fields', astra_fields)

    def _make_methods(self):
        # Replace fields to properties, make setters and getters
        cls = self.__class__
        if hasattr(cls, '_astra_precompiled'):
            return

        astra_fields = getattr(self.__class__, '_astra_fields')
        src_lines = []
        for fld in astra_fields.keys():
            field = astra_fields[fld]

            has_implement_get = hasattr(cls, 'get_%s' % fld)
            has_implement_set = hasattr(cls, 'set_%s' % fld)
            has_implement_del = hasattr(cls, 'del_%s' % fld)
            getter_name = 'get_%s' % fld
            setter_name = 'set_%s' % fld
            deleter_name = 'del_%s' % fld

            # o.field = 123 will call:
            # setter for field -> set_field(123) -> setattr('field', 123)
            if not has_implement_get:
                src_lines.append('def get_%s(self):' % fld)
                src_lines.append('  return self.getattr("%s")' % fld)
            if not has_implement_set:
                src_lines.append('def set_%s(self, value):' % fld)
                src_lines.append('  return self.setattr("%s", value)' % fld)
            if not has_implement_del:
                src_lines.append('def del_%s(self):' % fld)
                src_lines.append('  return self.setattr("%s", None)' % fld)

            if has_implement_get:
                getter_name = 'getattr(cls, "get_%s")' % fld
            if has_implement_set:
                setter_name = 'getattr(cls, "set_%s")' % fld
            if has_implement_del:
                setter_name = 'getattr(cls, "del_%s")' % fld
            src_lines.append('%s = property(%s, %s, %s, "%s Property")' % (
                fld, getter_name, setter_name, deleter_name,
                fld,))

            # Helpers code
            for helper_name in field.directly_redis_helpers:
                src_lines.append('def %s_%s(self, *args, **kwargs):' % (
                    fld, helper_name))
                src_lines.append('  return self.apply("%s", "%s", '
                                 '*args, **kwargs)' % (fld,
                                                       helper_name))

        src_code = '\n'.join(src_lines)
        global_scope = {'cls': cls}
        local_scope = {}
        exec(compile(src_code, '<string>', 'exec'), global_scope, local_scope)
        for kkk in local_scope:
            setattr(cls, kkk, local_scope[kkk])
        setattr(cls, '_astra_precompiled', True)

    def _get_original_field(self, field_name):
        field_key = '_astra_field_%s' % field_name
        if not hasattr(self, field_key):
            # Create instance from original field on demand
            astra_fields = getattr(self.__class__, '_astra_fields')
            try:
                target_field = astra_fields.get(field_name)
            except KeyError as e:
                raise AttributeError('%s key is not found' % field_name)
            new_instance = target_field.__class__(instance=True, model=self,
                                                  name=field_name,
                                                  db=self._astra_get_db(),
                                                  **target_field.options)
            setattr(self, field_key, new_instance)
            return new_instance
        return getattr(self, field_key)

    def _astra_get_db(self):
        if not self._astra_database:
            self._astra_database = self.get_db()
        return self._astra_database

    def __dir__(self):
        return [k for k in super(Model, self).__dir__() \
                if not k.startswith('_astra')]

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

    def __hash__(self):
        return hash('astra:%s:pk:%s' % (self.__class__.__name__, self.pk))

    def get_db(self):
        raise NotImplementedError('get_db method not implemented')

    def get_key_prefix(self, ):
        return '::'.join(['astra', self.__class__.__name__.lower()])

    def setattr(self, field_name, value):
        field = self._get_original_field(field_name)
        field.assign(value)

        if 'validators' in field.options:
            for validator in field.options['validators']:
                validator(value)
        return value

    def getattr(self, field_name):
        field = self._get_original_field(field_name)
        return field.obtain()

    def apply(self, field_name, helper_name, *args, **kwargs):
        field = self._get_original_field(field_name)
        f = field.get_helper_func(helper_name)
        return f(*args, **kwargs)

    def remove(self):
        # Remove all fields and one time delete entire hash
        is_hash_deleted = False

        astra_fields = getattr(self.__class__, '_astra_fields')
        for field_name in astra_fields.keys():
            field = self._get_original_field(field_name)
            if isinstance(field, base_fields.BaseHash):
                if not is_hash_deleted:
                    is_hash_deleted = True
                    field.db.delete(field.get_key_name(True))
            else:
                field.remove()
        self._astra_hash_exist = False

    def hash_exist(self):
        if self._astra_hash_exist is None:
            hash_found = False
            astra_fields = getattr(self.__class__, '_astra_fields')
            for field_name in astra_fields.keys():
                field = self._get_original_field(field_name)
                if isinstance(field, base_fields.BaseHash):
                    field.force_check_hash_exists()
                    hash_found = True
                    break
            if not hash_found:
                raise AttributeError('This model doesn\'t contain any hash')
        return self._astra_hash_exist
