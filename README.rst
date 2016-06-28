|PyPI Version| |Build Status|

==================
redis-astra
==================

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


Redis-astra supported signals, based on PyDispatcher:

.. code:: python

    from astra import signals

    def save_handler(**kwargs):
        print(kwargs)

    signals.post_init.connect(save_handler)
    signals.post_assign.connect(save_handler)

    >>> user = UserObject(pk=1, name="Mike", viewers=5)
    {'signal': 'post_init', 'instance': <Model UserObject(pk=1)>, 'sender': <class '__main__.UserObject'>}

    >>> user.login = 'mike@null.com'
    {'signal': 'post_assign', 'value': 'mike@null.com', 'instance': <Model UserObject(pk=1)>, 'attr': 'login', 'sender': <class '__main__.UserObject'>}


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