|PyPI Version| |Build Status|

======
redis-astra
======

Redis-astra is Python light ORM for Redis

Example:

.. code:: python

    import redis
    from astra import models

    db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)

    class SiteObject(models.Model):
        database = db
        name = models.CharHash()

    class UserObject(models.Model):
        database = db
        name = models.CharHash()
        login = models.CharHash()
        site_id = models.ForeignKeyHash(to='SiteObject')
        sites_list = models.List(to='SiteObject')
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
    >>> user.site_id = site
    >>> user.sites_list.lpush(site, site, site)
    3
    >>> len(user.sites_list)
    3
    >>> user.sites_list[2].name
    'redis.io'



Install
=======

Python versions 3.3, 3.4, 3.5 are supported.
Redis-py versions >= 2.9.1

.. code:: bash

    pip install redis-astra


.. |PyPI Version| image:: https://img.shields.io/pypi/v/redis-astra.png
   :target: https://pypi.python.org/pypi/redis-astra
.. |Build Status| image:: https://travis-ci.org/pilat/redis-astra.png
   :target: https://travis-ci.org/pilat/redis-astra