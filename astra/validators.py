import datetime as dt
import sys

from six import string_types, integer_types


# Validation rules common between hash and fields
class CharValidatorMixin(object):
    def _validate(self, value):
        if isinstance(value, bool):  # otherwise we've got "False" as value
            raise ValueError('Invalid type of field %s: %s.' %
                             (self._name, type(value).__name__))
        return value

    def _convert(self, value):
        return value  # may be none if hash is not exists


class BooleanValidatorMixin(object):
    def _validate(self, value):
        if not isinstance(value, bool):
            raise ValueError('Invalid type of field %s: %s. Expected is bool' %
                             (self._name, type(value).__name__))
        return '1' if bool(value) else '0'

    def _convert(self, value):
        return True if value == '1' else False


class IntegerValidatorMixin(object):
    def _validate(self, value):
        if not isinstance(value, integer_types):
            raise ValueError('Invalid type of field %s: %s. Expected is int' %
                             (self._name, type(value).__name__))
        return value

    def _convert(self, value):
        if value is None:
            return None
        try:
            return int(value)
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

    def _validate(self, value):
        if not isinstance(value, dt.datetime) and not \
                isinstance(value, dt.date):
            raise ValueError('Invalid type of field %s: %s. Expected '
                             'is datetime.datetime or datetime.date' %
                             (self._name, type(value).__name__))

        # return round(value.timestamp())  # without microseconds
        return value.strftime("%s")  # both class implements it

    def _convert(self, value):
        if not value:
            return value
        try:
            value = int(value)
        except ValueError:
            return None
        # TODO: maybe use utcfromtimestamp?.
        return dt.date.fromtimestamp(value)


class DateTimeValidatorMixin(DateValidatorMixin):
    def _convert(self, value):
        if not value:
            return value
        try:
            value = int(value)
        except ValueError:
            return None
        # TODO: maybe use utcfromtimestamp?.
        return dt.datetime.fromtimestamp(value)


class EnumValidatorMixin(object):
    def __init__(self, enum=list(), **kwargs):
        if 'instance' not in kwargs:
            # Instant when user define EnumHash. Definition test
            if len(enum) < 1:
                raise AttributeError("You're must define enum list")
            for item in enum:
                if not isinstance(item, string_types) or item == '':
                    raise ValueError("Enum list item must be string")
        self._enum = enum
        super(EnumValidatorMixin, self).__init__(enum=enum, **kwargs)

    def _validate(self, value):
        if value not in self._enum:
            raise ValueError('This value is not enumerate')
        return value

    def _convert(self, value):
        return value if value in self._enum else None


class ForeignObjectValidatorMixin(object):
    def __init__(self, to, **kwargs):
        super(ForeignObjectValidatorMixin, self).__init__(to=to, **kwargs)
        self._to = None
        if 'instance' not in kwargs:
            # First check
            from astra import models
            if not isinstance(to, string_types) \
                    and not isinstance(to, models.Model):
                raise AttributeError("You're must define to as string"
                                     " or Model class")
        else:
            # When object constructed, relation model can be loaded
            to_path = to.split('.')
            object_rel = to_path.pop()
            package_rel = '.'.join(to_path)
            if package_rel not in sys.modules.keys():
                package_rel = self._model.__class__.__module__
            if package_rel not in sys.modules.keys():
                raise AttributeError('Package "%s" is not loaded yet' % (to,))
            try:
                self._to = getattr(sys.modules[package_rel], object_rel)
            except AttributeError:
                pass  # TODO

    def _validate(self, value):
        if isinstance(value, bool):
            raise ValueError('Invalid type of field %s: %s.' %
                             (self._name, type(value).__name__))
        return value

    def _convert(self, value):
        return value