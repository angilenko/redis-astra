import uuid

from astra import models
import datetime as dt
import sys

PY_2 = sys.version_info[0] == 2
if PY_2:
    # Autoload only for Python 3 (see TestAutoImport for more info)
    from .other_models import SiteColorModel


class SiteObject(models.Model):
    # database = db

    prefix = 'custom_prefix'

    name = models.CharHash()
    tags = models.Set()  # Just a text set
    some_child = models.ForeignKey(to='ChildExample')  # type: ChildExample
    site_color = models.ForeignKey(to='tests.other_models.SiteColorModel',
                                   defaultPk=2)


class UserObject(models.Model):
    # database = db

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
    site_id = models.ForeignKey(to='SiteObject')
    site2 = models.ForeignKey(to='SiteObject', defaultPk=0)  # type: SiteObject

    credits_test = models.IntegerField()
    is_admin = models.BooleanField()

    sites_list = models.List(to='tests.sample_models.SiteObject')  # Redis Lists
    sites_set = models.Set(to='tests.sample_models.SiteObject')  # Redis Sets
    sites_sorted_set = models.SortedSet(
        to='tests.sample_models.SiteObject')  # Redis Sorted Sets


class ParentExample(models.Model):
    # database = db

    _ts = models.DateTimeHash()  # Creation time
    parent_field = models.CharHash()

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
