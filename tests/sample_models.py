import redis
import uuid

from astra import models
import datetime as dt
from six import PY2


if PY2:
    # Autoload only for Python 3 (see TestAutoImport for more info)
    from .other_models import SiteColorModel


db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)


def site_name_validator(value):
    if len(value) > 32:
        raise ValueError('Site name must be less 32 characters')


class SiteObject(models.Model):
    name = models.CharHash(validators=[site_name_validator])
    tags = models.Set()  # Just a text set
    some_child = models.ForeignKey(to='tests.sample_models.ChildExample')
    site_color = models.ForeignKey(to='tests.other_models.SiteColorModel',
                                   defaultPk=2)

    def get_db(self):
        return db


class UserObject(models.Model):
    status_choice = (
        'REGISTERED',
        'ACTIVATED',
        'BANNED',
    )

    name = models.CharHash()
    login = models.CharHash()
    rating = models.IntegerHash()
    paid = models.BooleanHash()
    registration_date = models.DateHash()
    last_login = models.DateTimeHash()
    status = models.EnumHash(enum=status_choice, default='REGISTERED')
    inviter = models.ForeignKey(to='tests.sample_models.UserObject')
    site1 = models.ForeignKey(to=SiteObject)
    site2 = models.ForeignKey(to='tests.sample_models.SiteObject', defaultPk=0)

    credits_test = models.IntegerField()
    is_admin = models.BooleanField()

    sites_list = models.List(to='tests.sample_models.SiteObject')
    sites_set = models.Set(to='tests.sample_models.SiteObject')
    sites_sorted_set = models.SortedSet(to='tests.sample_models.SiteObject')

    def get_db(self):
        return db


class ParentExample(models.Model):
    _ts = models.DateTimeHash()  # Creation time
    parent_field = models.CharHash()

    def get_db(self):
        return db

    def __init__(self, pk=None, **kwargs):
        """ Custom designer can act as a PK generator """
        if not pk:
            super(ParentExample, self).__init__(uuid.uuid4().hex, **kwargs)
            self._ts = dt.datetime.now()
        elif pk:
            super(ParentExample, self).__init__(pk, **kwargs)

    @property
    def exist(self):
        return True if self._ts else False


class ChildExample(ParentExample):
    field1 = models.CharHash()
    field2 = models.CharHash()
