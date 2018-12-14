from astra import models
import redis


db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)


class SiteColorModel(models.Model):
    color = models.CharField()

    def get_db(self):
        return db
