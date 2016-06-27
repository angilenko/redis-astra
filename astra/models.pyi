# Stub file for syntax highlighting

class List:
    def lindex(self, index):
        pass

    def linsert(self, where, refvalue, value):
        pass

    def llen(self):
        pass

    def lpop(self):
        pass

    def lpush(self, *values):
        pass

    def lpushx(self, value):
        pass

    def lrange(self, start, end):
        pass

    def lrem(self, count, value):
        pass

    def lset(self, index, value):
        pass

    def ltrim(self, start, end):
        pass

    def rpop(self):
        pass

    def rpoplpush(self, src, dst):
        pass

    def rpush(self, *values):
        pass

    def rpushx(self, value):
        pass


class Set:
    def sadd(self, *values):
        pass

    def scard(self):
        pass

    def sdiff(self, keys, *args):
        pass

    def sdiffstore(self, keys, *args):
        pass

    def sinter(self, keys, *args):
        pass

    def sinterstore(self, keys, *args):
        pass

    def sismember(self, value):
        pass

    def smembers(self):
        pass

    def smove(self, src, dst, value):
        pass

    def spop(self):
        pass

    def srandmember(self, number=None):
        pass

    def srem(self, *values):
        pass

    def sunion(self, keys, *args):
        pass

    def sunionstore(self, keys, *args):
        pass

    def sscan(self, cursor=0, match=None, count=None):
        pass


class SortedSet:
    def zadd(self, *args, **kwargs):
        pass

    def zcard(self):
        pass

    def zcount(self, min, max):
        pass

    def zincrby(self, value, amount=1):
        pass

    def zinterstore(self, keys, aggregate=None):
        pass

    def zlexcount(self, min, max):
        pass

    def zrange(self, start, end, desc=False, withscores=False,
               score_cast_func=float):
        pass

    def zrangebylex(self, min, max, start=None, num=None):
        pass

    def zrangebyscore(self, min, max, start=None, num=None,
                      withscores=False, score_cast_func=float):
        pass

    def zrank(self, value):
        pass

    def zrem(self, *values):
        pass

    def zremrangebylex(self, min, max):
        pass

    def zremrangebyrank(self, min, max):
        pass

    def zremrangebyscore(self, min, max):
        pass

    def zrevrange(self, start, end, withscores=False,
                  score_cast_func=float):
        pass

    def zrevrangebylex(self, max, min, start=None, num=None):
        pass

    def zrevrangebyscore(self, max, min, start=None, num=None,
                         withscores=False, score_cast_func=float):
        pass

    def zrevrank(self, value):
        pass

    def zscan(self, cursor=0, match=None, count=None,
              score_cast_func=float):
        pass

    def zscore(self, value):
        pass

    def zunionstore(self, keys, aggregate=None):
        pass