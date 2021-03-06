|PyPI Version| |Build Status|

==================
redis-astra
==================

Redis-astra is Python light ORM for Redis.

*Note*: version 2 has uncomportable changes with version 1. See `CHANGELOG.txt <https://github.com/pilat/redis-astra/blob/master/CHANGELOG.txt>`_


Base Example:

.. code:: python

    import redis
    from astra import models

    db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)

    class SiteObject(models.Model):
        def get_db(self):
            return db
        
        name = models.CharHash()

    class UserObject(models.Model):
        def get_db(self):
            return db
        
        name = models.CharHash()
        login = models.CharHash()
        site = models.ForeignKey(to=SiteObject)
        sites_list = models.List(to=SiteObject)
        viewers = models.IntegerField()


So you can use it like this:

.. code:: python

    >>> user = UserObject(pk=1, name="Mike", viewers=5)
    >>> user.login = 'mike@null.com'
    >>> user.login
    'mike@null.com'
    >>> user.viewers_incr(2)
    7
    >>> site = SiteObject(pk=1, name="redis.io")
    >>> user.site = site
    >>> user.sites_list.lpush(site, site, site)
    3
    >>> len(user.sites_list)
    3
    >>> user.sites_list[2].name
    'redis.io'
    >>> user.site = None
    >>> user.remove()



You can override some methods for track data changes. For example:

.. code:: python

    import redis
    from astra import models

    db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)

    class User(models.Model):
        def get_db(self):
            return db
        
        name = models.CharHash()
        login = models.CharHash()
        
        def set_name(self, value):
            self.setattr('name', '%s_was_changed' % value)
        
        def set_login(self, value):
            if '@' not in value:
                raise ValueError('Invalid login')
            self.setattr('login', value)

        def setattr(self, field_name, value):
            if field_name == 'name':
                print('Old name: %s' % self.name)
                print('Set new name: %s' % value)
            
            super().setattr(field_name, value)

    u = User(1, name='Alice', login='new@localhost')
    >> Old name: 
    >> Set new name: Alice_was_changed
    u.login
    >> 'new@localhost'
    u.login = 'newlogin'
    >> .. ValueError: Invalid login
    u.login = 'newlogin@localhost'
    u.name = 'New name'
    >> Old name: Alice_was_changed
    >> Set new name: New name_was_changed



Install
==================

Python versions 2.6, 2.7, 3.3, 3.4, 3.5 are supported
Redis-py versions >= 2.9.1

.. code:: bash

    pip install redis-astra


.. |PyPI Version| image:: https://img.shields.io/pypi/v/redis-astra.png
   :target: https://pypi.python.org/pypi/redis-astra
.. |Build Status| image:: https://travis-ci.org/pilat/redis-astra.png
   :target: https://travis-ci.org/pilat/redis-astra