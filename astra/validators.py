import datetime as dt
from six import string_types, integer_types, PY2


# Validation rules common between hash and fields
class CharValidatorMixin(object):
    def _convert_set(self, value):
        if not isinstance(value, string_types):
            raise ValueError('String expected, but %s was given for '
                             'field %s ' % (type(value).__name__, self.name))
        return value

    def _convert_get(self, value):
        return value or ''


class BooleanValidatorMixin(object):
    def _convert_set(self, value):
        if not isinstance(value, bool):
            raise ValueError('Boolean expected, but %s was given for '
                             'field %s ' % (type(value).__name__, self.name))
        return '1' if bool(value) else '0'

    def _convert_get(self, value):
        return True if value == '1' else False


class IntegerValidatorMixin(object):
    def _convert_set(self, value):
        if not isinstance(value, integer_types):
            raise ValueError('Integer expected, but %s was given for '
                             'field %s ' % (type(value).__name__, self.name))
        return str(value)

    def _convert_get(self, value):
        try:
            return int(value or 0)
        except ValueError:
            return None


class DateValidatorMixin(object):
    """
        We're store only seconds on redis. Using microseconds leads to subtle
        errors:
            import datetime
            datetime.datetime.fromtimestamp(t)
            (2016, 3, 3, 12, 20, 30, 2) when t = 1457007630.000002, but
            (2016, 3, 3, 12, 20, 30) when t = 1457007630.000001
        """

    def _convert_set(self, value):
        if not isinstance(value, (dt.datetime, dt.date,)):
            raise ValueError('Datetime or date expected, but %s was given for '
                             'field %s ' % (type(value).__name__, self.name))

        # return round(value.timestamp())  # without microseconds
        return value.strftime('%s')  # both class implements it

    def _convert_get(self, value):
        try:
            value = int(value or 0)
        except ValueError:
            return None
        # TODO: maybe use utcfromtimestamp?.
        return dt.date.fromtimestamp(value)


class DateTimeValidatorMixin(DateValidatorMixin):
    def _convert_get(self, value):
        try:
            value = int(value or 0)
        except ValueError:
            return None
        # TODO: maybe use utcfromtimestamp?.
        return dt.datetime.fromtimestamp(value)


class EnumValidatorMixin(object):
    def __init__(self, enum=list(), default='', **kwargs):
        if 'instance' not in kwargs:
            # Instant when user define EnumHash. Definition test
            if len(enum) < 1:
                raise AttributeError('You\'re must define enum list')
            for item in enum:
                if not isinstance(item, string_types) or item == '':
                    raise ValueError('Enum list item must be string')
            if default not in enum:
                raise ValueError('The default value is not present '
                                 'in the enum list')
        self._enum = enum
        self._enum_default = default
        super(EnumValidatorMixin, self).__init__(
            enum=enum, default=default, **kwargs)

    def _convert_set(self, value):
        if value not in self._enum:
            raise ValueError('This value is not enumerate')
        return value

    def _convert_get(self, value):
        return value if value in self._enum else self._enum_default


class ForeignObjectValidatorMixin(object):
    def __init__(self, to=None, defaultPk=None, **kwargs):
        super(ForeignObjectValidatorMixin, self).__init__(
            to=to, defaultPk=defaultPk, **kwargs)
        self._defaultPk = defaultPk

        if to is None:
            return

        if 'instance' in kwargs:
            # Replace _to method to foreign constructor
            if isinstance(to, string_types):
                import sys
                to_path = to.split('.')
                object_rel = to_path.pop()
                package_rel = '.'.join(to_path)

                if PY2:
                    import imp as _imp
                else:
                    import _imp

                _imp.acquire_lock()
                module1 = __import__('.'.join(to_path))
                _imp.release_lock()

                try:
                    self._to = getattr(sys.modules[package_rel], object_rel)
                except AttributeError:
                    raise AttributeError('Package "%s" not contain model %s' %
                                        (package_rel, object_rel))
            else:
                self._to = to

    def _convert_set(self, value):
        from astra import model
        if isinstance(value, model.Model):
            return value.pk
        elif isinstance(value, string_types + integer_types):
            return value
        
        raise ValueError('Model instance, string or integer are expected, '
                            'but %s was given for field %s ' % (
                                type(value).__name__, self.name))

    def _convert_get(self, value):
        return value

    def _to(self, key):
        # Return string key when for models.ForeignKey not specified "to"
        # attribute. e.g. author_id = models.ForeignKey()
        return key

    def _to_wrapper(self, key):
        if key is None:
            if self._defaultPk is not None:
                return self._to(self._defaultPk)
            else:
                return None

        return self._to(key)
