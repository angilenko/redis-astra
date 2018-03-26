|PyPI Version| |Build Status|

==================
redis-astra
==================

Redis-astra is Python light ORM for Redis.

*Note*: version 2 has uncomportable changes with version 1. See `CHANGELOG.txt <https://github.com/pilat/redis-astra/blob/master/CHANGELOG.txt>`_


Example:

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

        def save(self, action, attr=None, value=None):            
            print('\t * %s' % kwargs)


So you can use it like this:

.. code:: python

    >>> user = UserObject(pk=1, name="Mike", viewers=5)
    	* {'action': 'post_init', 'value': {'name': 'Mike', 'viewers': 5}}
    >>> user.login = 'mike@null.com'
        * {'action': 'pre_assign', 'attr': 'login', 'value': 'mike@null.com'}
	    * {'action': 'post_assign', 'attr': 'login', 'value': 'mike@null.com'}
    >>> user.login
    'mike@null.com'
    >>> user.viewers_incr(2)
    7
    >>> site = SiteObject(pk=1, name="redis.io")
    >>> user.site = site
        * {'attr': 'site', 'action': 'm2m_link', 'value': <Model SiteObject(pk=1)>}
    >>> user.sites_list.lpush(site, site, site)
    3
    >>> len(user.sites_list)
    3
    >>> user.sites_list[2].name
    'redis.io'
    >>> user.site = None
	    * {'attr': 'site', 'action': 'm2m_remove'}
    >>> user.remove()
        * {'action': 'pre_remove', 'attr': 'pk', 'value': '1'}
        * {'action': 'post_remove', 'attr': 'pk', 'value': '1'}



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