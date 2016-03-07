from astra import models


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
    is_admin = models.BooleanField()  # Other types like hash

    sites_list = models.List(to='tests.sample_model.SiteObject')  # Redis Lists
    sites_set = models.Set(to='tests.sample_model.SiteObject')  # Redis Sets
    sites_sorted_set = models.SortedSet(
        to='tests.sample_model.SiteObject')  # Redis Sorted Sets
