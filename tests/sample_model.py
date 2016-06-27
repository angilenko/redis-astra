import uuid

from astra import models
import datetime as dt


class SiteObject(models.Model):
    prefix = 'custom_prefix'

    name = models.CharHash()


class UserObject(models.Model):
    status_choice = (
        'REGISTERED',
        'ACTIVATED',
        'BANNED',
    )
    # database = db

    name = models.CharHash()
    login = models.CharHash()
    rating = models.IntegerHash()
    paid = models.BooleanHash()
    registration_date = models.DateHash()
    last_login = models.DateTimeHash()
    status = models.EnumHash(enum=status_choice)
    inviter = models.ForeignKeyHash(to='tests.sample_model.UserObject')
    site_id = models.ForeignKey(to='SiteObject')

    credits_test = models.IntegerField()
    is_admin = models.BooleanField()

    sites_list = models.List(to='tests.sample_model.SiteObject')  # Redis Lists
    sites_set = models.Set(to='tests.sample_model.SiteObject')  # Redis Sets
    sites_sorted_set = models.SortedSet(
        to='tests.sample_model.SiteObject')  # Redis Sorted Sets


class ParentExample(models.Model):
    # database = db

    _ts = models.DateTimeHash()  # Creation time
    parent_field = models.CharHash()

    def __init__(self, pk=None, **kwargs):
        """ Custom designer can act as a PK generator """
        if not pk:
            super().__init__(uuid.uuid4().hex, **kwargs)
            self._ts = dt.datetime.now()
        elif pk:
            super().__init__(pk, **kwargs)

    @property
    def exist(self):
        return True if self._ts else False


class ChildExample(ParentExample):
    field1 = models.CharHash()
    field2 = models.CharHash()
