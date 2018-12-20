import datetime as dt
import pytest
import redis
from six import PY2
from astra import models

from .sample_models import UserObject, SiteObject, ParentExample, ChildExample


if not PY2:
    from unittest.mock import MagicMock, call, patch


# Patch redis. Connection method for collect command sequences for this test
def patched_send_command(self, *args):
    if 'commands' in globals():
        commands.append(args)
    self.send_packed_command(self.pack_command(*args))


redis.Connection.send_command = patched_send_command


# Common class for simplify testing
class CommonHelper:
    def setup(self):
        global db, commands
        db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)

        UserObject.get_db = self._get_db
        SiteObject.get_db = self._get_db
        ParentExample.get_db = self._get_db

        db.flushall()
        commands = []

    def _get_db(self):
        global db
        return db

    def setup_method(self, test_method):
        pass

    def teardown_method(self, test_method):
        pass

    # Helpers
    def assert_commands_count(self, count):
        assert len(commands) == count, commands

    def assert_keys_count(self, count):
        assert len(db.keys()) == count

    # primitive mock for testing on Python 2
    def simple_mock(self, *args, **kwargs):
        if not hasattr(self, 'mock_calls'):
            self.mock_calls = 0
        self.mock_calls += 1


# Test of base fields behavior
class TestModelField(CommonHelper):
    def test_primary_key_is_always_string(self):
        user = UserObject(1)
        user.name = 'Username'
        user2 = UserObject('1')
        assert user2.name == 'Username'

    def test_set_and_read_model_attrs(self):
        user1 = UserObject(1)
        user1.name = 'Username'
        assert user1.name == 'Username'
        user1.name = '12345'
        assert user1.name == '12345'
        self.assert_commands_count(3)

    def test_remove_object(self):
        user1 = UserObject(1)
        user1.name = 'Username'
        user1.remove()
        self.assert_keys_count(0)

    def test_set_attrs_via_kwargs(self):
        user1 = UserObject(1, name='Username')
        assert user1.name == 'Username'

        user2 = UserObject(name='Username', pk=2)
        assert user2.name == 'Username'

    def test_default_values(self):
        user1 = UserObject(1)
        assert isinstance(user1.name, str)
        assert user1.name == ''
        assert isinstance(user1.is_admin, bool)
        assert user1.is_admin is False
        assert isinstance(user1.rating, int)
        assert user1.rating == 0

    def test_pk_already_string(self):
        user1 = UserObject(1)
        assert isinstance(user1.pk, str)
        user1 = UserObject('2')
        assert isinstance(user1.pk, str)

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_redis_pass_arg_directly(self):
        db.hset = MagicMock()
        user1 = UserObject(1)
        user1.login = '1234'
        # redis independently convert key to string
        db.hset.assert_called_once_with('astra::userobject::hash::1',
                                        'login', '1234')

    def test_success_saved(self):
        user_write = UserObject(1)
        user_write.name = 'Username'
        user_write.login = 'user@null.com'

        user_read = UserObject(1)
        assert user_read.name == 'Username'
        assert user_read.login == 'user@null.com'
        self.assert_commands_count(3)

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_read_real_value(self):
        db.hgetall = MagicMock(return_value={'name': 'Username'})
        user1 = UserObject(1)
        assert user1.name == 'Username'
        assert user1.login == ''

    def test_value_after_save(self):
        user_write = UserObject(1)
        user_write.login = 'user@null.com'
        assert user_write.login == 'user@null.com'
        self.assert_commands_count(2)  # We're can improve it?

    def test_check_prop_after_double_save(self):
        user_write = UserObject(1)
        user_write.name = 'Username'
        user_write.login = 'user@null.com'
        user_write.name = 'Username'
        assert user_write.name == 'Username'

        user_read = UserObject(1)
        assert user_read.name == 'Username'

    def test_with_using_helper(self):
        user1 = UserObject(1)
        user1.credits_test_setex(10, 214)  # value: 214, 10 second ttl
        assert user1.credits_test == 214

    def test_hash_exists1(self):
        user1 = UserObject(1, name='Test')
        assert user1.hash_exist() is True

    def test_hash_exists2(self):
        user1 = UserObject(1, name='Test')
        read_user1 = UserObject(1)
        assert read_user1.hash_exist() is True

    def test_hash_non_exists(self):
        user2 = UserObject(2)
        assert user2.hash_exist() is False

    def test_model_without_hash(self):
        class SampleObject(models.Model):
            name = models.CharField()

            def get_db(self):
                return db
        test_object = SampleObject(1, name='Alice')
        with pytest.raises(AttributeError):
            a = test_object.hash_exist()

    def test_alt_keys_prefixes(self):
        class SampleObject(models.Model):
            name = models.CharField()
            def get_db(self):
                return db
            def get_key_prefix(self):
                return 'custom::tst_%s_tst' % self.__class__.__name__.lower()

        SampleObject(1, name='Alice')
        assert len(commands) == 1
        assert commands[0][1] == 'custom::tst_sampleobject_tst::fld::1::name'


# Test hash fields with value conversions:
class TestBaseHash(CommonHelper):
    def test_none_to_char_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.login = None
        self.assert_commands_count(0)

    def test_false_to_char_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.login = False
        self.assert_commands_count(0)

    def test_number_to_char_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.login = 12345
        self.assert_commands_count(0)


class TestIntegerHash(CommonHelper):
    def test_none_to_int_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.rating = None

    def test_char_to_int_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.rating = '23'

    def test_float_to_int_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.rating = 5.2
        self.assert_commands_count(0)

    def test_char_to_int_type_conversion(self):
        user1 = UserObject(1)
        user1.rating = 5  # convert to str on redis
        user1_read = UserObject(1)
        assert user1_read.rating == 5  # convert back to user type


class TestBooleanHash(CommonHelper):
    def test_save_not_boolean_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.paid = 1

    def test_save_boolean(self):
        user1 = UserObject(1)
        user1.paid = True
        user1_read = UserObject(1)
        assert user1_read.paid is True


class TestDateHash(CommonHelper):
    def test_empy_date(self):
        user1 = UserObject(1)
        assert user1.registration_date is not None

    def test_save_not_date_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.registration_date = '2015-01-01'  # invalid

    def test_save_date(self):
        my_date = dt.date(2016, 3, 2)
        user1 = UserObject(1)
        user1.registration_date = my_date
        user1_read = UserObject(1)
        assert user1_read.registration_date == my_date


class TestDateTimeHash(CommonHelper):
    def test_save_not_date_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.last_login = 2123214121

    def test_save_datetime(self):
        # Don't use now()
        # my_date = datetime.utcnow().replace(tzinfo=utc)
        my_date = dt.datetime(2016, 3, 3, 12, 20, 30)
        user1 = UserObject(1)
        user1.last_login = my_date
        user1_read = UserObject(1)
        assert user1_read.last_login == my_date

    def test_save_date_instead_datetime(self):
        my_date = dt.date(2016, 3, 2)
        user1 = UserObject(1)
        user1.last_login = my_date
        user1_read = UserObject(1)
        assert type(user1_read) is not type(my_date)  # return datetime
        assert user1_read.last_login.day == my_date.day
        assert user1_read.last_login.month == my_date.month
        assert user1_read.last_login.year == my_date.year


class TestEnumHash(CommonHelper):
    def test_invalid_model_define_exception(self):
        with pytest.raises(AttributeError):
            class SampleObject1(models.Model):
                field = models.EnumHash()

        with pytest.raises(ValueError):
            class SampleObject2(models.Model):
                field = models.EnumHash(enum=('',), default='')

        with pytest.raises(ValueError):
            class SampleObject3(models.Model):
                field = models.EnumHash(enum=(123, '43'), default='43')

    def test_get_enum_default_value(self):
        user1 = UserObject(1)
        assert user1.status == 'REGISTERED'

    def test_save_not_enum_value(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.status = 'INVALID_ENUM'

    def test_save_correct_enum_value(self):
        user1 = UserObject(1)
        user1.status = UserObject.status_choice[1]  # ACTIVATED
        user1_read = UserObject(1)
        assert user1_read.status == UserObject.status_choice[1]


class TestHashDelete(CommonHelper):
    def test_deleted_operations_count(self):
        class SampleObject1(models.Model):
            name = models.CharHash()
            rating = models.IntegerHash()
            field1 = models.CharField()

            def get_db(self):
                return db
        test_object = SampleObject1(1, name='Alice', rating=22, field1='test')
        self.assert_commands_count(3)  # two times set hash + field
        test_object.remove()
        self.assert_commands_count(5)  # one time delete entire hash + field


class TestLinkField(CommonHelper):
    def test_save_foreign_link_as_object(self):
        site1 = SiteObject(1, name='redis.io')
        UserObject(1, name='Username', site1=site1)

        user_reader1 = UserObject(1)
        assert user_reader1.site1.pk == '1'
        assert isinstance(user_reader1.site1, SiteObject)

    def test_save_foreign_link_as_string(self):
        site2 = SiteObject(2)
        site2.name = 'redis.io'

        UserObject(1, name='Username', site1='2')

        user_reader1 = UserObject(1)
        assert user_reader1.site1.pk == '2'
        assert user_reader1.site1.name == 'redis.io'
        assert isinstance(user_reader1.site1, SiteObject)

    def test_foreign_link_remove(self):
        site1 = SiteObject(1, name='redis.io')
        UserObject(1, name='Username', site1=site1)

        user1 = UserObject(1)
        user1.site1 = None

        user2 = UserObject(1)
        assert user2.site1 is None


class TestIntegerField(CommonHelper):
    def test_save_not_integer_value(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.credits_test = 'abc1'

    def test_save_valid_value(self):
        user1 = UserObject(1)
        user1.credits_test = 5
        user1_read = UserObject(1)
        assert user1_read.credits_test == 5

    def test_incremental_and_decremental(self):
        user1 = UserObject(1)
        user1.credits_test = 11

        user1_modified = UserObject(1)
        assert user1_modified.credits_test == 11
        user1_modified.credits_test_incr(1)
        assert user1_modified.credits_test == 12

        user1_read = UserObject(1)
        assert user1_read.credits_test == 12

        user1_modified = UserObject(1)
        user1_modified.credits_test_decr(2)
        assert user1_modified.credits_test == 10

        user1_read = UserObject(1)
        assert user1_read.credits_test == 10


class TestBooleanField(CommonHelper):
    def test_save_not_boolean_exception(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.is_admin = 1

    def test_save_boolean(self):
        user1 = UserObject(1)
        user1.is_admin = True
        user1_read = UserObject(1)
        assert user1_read.is_admin is True
        assert user1_read.is_admin is True
        self.assert_commands_count(3)  # one set and two get

    def test_save_boolean_and_read_twice(self):
        user1 = UserObject(1)
        user1.is_admin = False
        assert user1.is_admin is False
        assert user1.is_admin is False


class TestFieldDelete(CommonHelper):
    def test_invalidate_when_remove(self):
        user1 = UserObject(pk=1, credits_test=20)
        instance_user1 = UserObject(1)
        user1.remove()
        assert user1.credits_test == 0
        assert instance_user1.credits_test == 0


class TestList(CommonHelper):
    def test_append_to_list_left_and_right(self):
        site1 = SiteObject(1, name='redis.io')
        site2 = SiteObject(2, name='google.com')
        site3 = SiteObject(3, name='yahoo.com')

        user1 = UserObject(1)
        user1.sites_list.lpush(site1)
        user1.sites_list.lpush(site2, site3)
        user1.sites_list.lpushx(value=site2)  # pass by kwarg
        user1.sites_list.rpush(site3)

        user1_read = UserObject(1)
        assert user1_read.sites_list.llen() == 5
        assert user1_read.sites_list.lindex(2) == SiteObject(2)

    def test_invalid_index(self):
        user1 = UserObject(1)
        assert user1.sites_list.lindex(100) is None

    def test_invalid_pop(self):
        user1 = UserObject(1)
        assert user1.sites_list.lpop() is None
        assert user1.sites_list.rpop() is None

    def test_empty_range(self):
        user1 = UserObject(1)
        assert user1.sites_list.lrange('-1', '1000') == []

    def test_valid_range(self):
        sites_list = []
        for i in range(1, 4):
            sites_list.append(SiteObject(i))
        assert len(sites_list) == 3

        user1 = UserObject(1)
        user1.sites_list.lpush(*sites_list)

        user1_read = UserObject(1)
        answer_list = user1_read.sites_list.lrange(0, -1)  # All
        assert len(answer_list) == 3
        assert isinstance(answer_list[0], SiteObject)
        for site in sites_list:
            assert site in answer_list

    def test_separate_fields(self):
        site1 = SiteObject('id1')
        site2 = SiteObject('id2')

        user1 = UserObject(1)
        user2 = UserObject(2)
        user1.sites_list.lpush(site1)
        user2.sites_list.lpush(site2)

        user1_read = UserObject(1)
        user2_read = UserObject(2)
        site1_user1_pop = user1_read.sites_list.lpop()
        site1_user2_pop = user2_read.sites_list.lpop()
        self.assert_commands_count(4)  # 2xPUSH and 2xPOP

        assert site1.pk == site1_user1_pop.pk
        assert site2.pk == site1_user2_pop.pk

    def test_get_by_slice(self):
        site1 = SiteObject('id2')
        site2 = SiteObject('id1')
        site3 = SiteObject('id0')

        user1 = UserObject(1)
        user1.sites_list.lpush(site1, site2)
        user1.sites_list.rpush(site3)

        user1_read = UserObject(1)
        slice1 = user1_read.sites_list[1:2]
        assert len(slice1) == 2
        assert slice1[0] == site1

    def test_erase_list(self):
        user1 = UserObject(1, name='User123')
        site1 = SiteObject('id1')
        user1.sites_list.lpush(site1)
        assert len(user1.sites_list) == 1
        # user1.sites_list = None
        user1.remove()
        self.assert_keys_count(0)


class TestSimpleSet(CommonHelper):
    def test_without_foreign(self):
        site = SiteObject(1)
        site.tags.sadd('games')
        site.tags.sadd('shooter')
        assert site.tags.sismember('games') is True
        assert site.tags.sismember('shooter') is True
        assert site.tags.sismember('business') is False

    def test_convert_to_str(self):
        site = SiteObject(1)
        site.tags.sadd(123)
        assert site.tags.sismember(123) is True
        assert site.tags.sismember('123') is True
        assert site.tags.sismember(456) is False

    def test_get_items(self):
        site = SiteObject(1)
        site.tags.sadd('fast')
        site.tags.sadd('bootstrap')
        ret = site.tags.smembers()
        assert isinstance(ret, list)
        assert 'fast' in ret
        assert 'magenta' not in ret


class TestSet(CommonHelper):
    def test_len(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)

        # Lists contains only one item with same value
        user1 = UserObject(1)
        user1.sites_set.sadd(site1)
        user1.sites_set.sadd(site1)
        user1.sites_set.sadd(site2)

        user1_read = UserObject(1)
        assert user1_read.sites_set.scard() == 2

    def test_is_member(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)

        user1 = UserObject(1)
        user1.sites_set.sadd(site1, site2)

        user1_read = UserObject(1)
        site3 = SiteObject(3)
        assert user1_read.sites_set.sismember(site3) is False

    def test_pop(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)

        user1 = UserObject(1)
        user1.sites_set.sadd(site1)
        user1.sites_set.sadd(site1)
        user1.sites_set.sadd(site2)

        user1_read = UserObject(1)
        read_site = user1_read.sites_set.spop()
        # Remember that the order in sets is not respected:
        assert read_site == site2 or read_site == site1

    def test_erase_set(self):
        user1 = UserObject(1, name='User123')
        site1 = SiteObject('id1')
        user1.sites_set.sadd(site1)
        assert len(user1.sites_set) == 1
        user1.sites_set = None
        user1.remove()
        self.assert_keys_count(0)


class TestSortedSet(CommonHelper):
    def test_add_and_zrange(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)
        user1 = UserObject(1)
        # Add items score, member, score, member, ...
        user1.sites_sorted_set.zadd(100, site1, 300, site2, 200, site1)

        user1_read = UserObject(1)
        answered_list = user1_read.sites_sorted_set.zrange(1, 1)
        assert len(answered_list) == 1
        assert answered_list[0] == site2

    def test_add_and_zrange_by_score(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)
        user1 = UserObject(1)
        # Add items score, member, score, member, ...
        user1.sites_sorted_set.zadd(100, site1, 300, site2, 200, site1)
        assert user1.sites_sorted_set.zcard() == 2  # only original objects

        user1_read = UserObject(1)
        answered_list = user1_read.sites_sorted_set.zrangebyscore(201, 300)
        assert len(answered_list) == 1
        assert answered_list[0] == site2

    def test_get_with_scores(self):
        user1 = UserObject(1)
        for i in range(1, 10):
            site = SiteObject(i)
            user1.sites_sorted_set.zadd(i*100, site)

        with_scores = user1.sites_sorted_set.zrangebyscore('-inf', '+inf',
                                                           withscores=True)
        assert isinstance(with_scores, list)
        first_item = with_scores[0]
        assert isinstance(first_item, tuple)
        assert isinstance(first_item[0], SiteObject)
        assert isinstance(first_item[1], float)

    def test_get_by_slice(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)
        site3 = SiteObject(3)
        user1 = UserObject(1)
        user1.sites_sorted_set.zadd(100, site1, 200, site2, 300, site3)

        user1_read = UserObject(1)
        result_slice = user1_read.sites_sorted_set[200:300]
        assert result_slice[0] == site2
        assert result_slice[1] == site3

    def test_rem_by_score(self):
        site1 = SiteObject(1)
        site2 = SiteObject(2)
        site3 = SiteObject(3)
        user1 = UserObject(1)
        user1.sites_sorted_set.zadd(100, site1, 200, site2, 300, site3)

        user1_modified = UserObject(1)
        user1_modified.sites_sorted_set.zremrangebyscore(100, 200)

        user1_read = UserObject(1)
        # reverse get:
        answered_list = user1_read.sites_sorted_set.zrevrangebyscore('+inf',
                                                                     '-inf')
        assert len(answered_list) == 1
        assert answered_list[0] == site3

    def test_erase_sorted_set(self):
        user1 = UserObject(1, name='User123')
        site1 = SiteObject('id1')
        user1.sites_sorted_set.zadd(1, site1)
        assert len(user1.sites_sorted_set) == 1
        user1.sites_sorted_set = None
        user1.remove()
        self.assert_keys_count(0)


class TestParentInheritance(CommonHelper):
    def test_set_and_get(self):
        child1 = ChildExample()  # Custom constructor generates unique pk
        child1.parent_field = 'test0'
        child1.field1 = 'test1'

        child1_id = child1.pk

        read_child = ChildExample(child1_id)
        assert read_child.parent_field == 'test0'
        assert read_child.field1 == 'test1'


class TestAttsBase(CommonHelper):
    def test_set_prop(self):
        user1 = UserObject(1)
        user1.name = 'User123'
        assert UserObject(1).name == 'User123'

    def test_set_prop_on_init(self):
        user1 = UserObject(1, name='User123')
        assert UserObject(1).name == 'User123'

    def test_set_prop_by_setter(self):
        user1 = UserObject(1)
        user1.set_name('User123')
        assert UserObject(1).name == 'User123'

    def test_set_prop_by_setattr(self):
        user1 = UserObject(1)
        user1.setattr('name', 'User123')
        assert UserObject(1).name == 'User123'

    def test_get_prop_by_getter(self):
        user1 = UserObject(1, name='User123')
        assert UserObject(1).get_name() == 'User123'

    def test_get_prop_by_getprop(self):
        user1 = UserObject(1, name='User123')
        assert UserObject(1).getattr('name') == 'User123'


class TestAttrsExtend(CommonHelper):
    @pytest.mark.parametrize('field_type', [
        models.CharHash,
        models.CharField
    ])
    def test_value_on_save(self, field_type):
        class SampleObject1(models.Model):
            name = field_type()
            description = field_type()

            def get_db(self):
                return db

            def setattr(self, field_name, value):
                if field_name == 'name':
                    value = '%s_was_changed' % value
                return super(SampleObject1, self).setattr(field_name, value)

        test_object = SampleObject1(1)
        test_object.name = 'name'
        test_object.description = 'description'
        assert test_object.name == 'name_was_changed'
        assert test_object.description == 'description'

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_track_changes(self):
        with patch.object(UserObject, 'setattr',
                          side_effect=['User1', 5]) as mo:
            user1 = UserObject(1, name='User1')
            user1.rating = 5
            mo.assert_has_calls([
                call('name', 'User1'),
                call('rating', 5),
            ], any_order=True)

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_m2m_link_signal(self):
        site = SiteObject(pk=1, name="redis.io")
        with patch.object(UserObject, 'setattr', return_value=None) as mo:
            user1 = UserObject(1)
            user1.site1 = site
            mo.assert_called_with('site1', site)

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_m2m_remove_signal(self):
        site = SiteObject(pk=1, name="redis.io")
        user1 = UserObject(1)
        user1.site1 = site
        with patch.object(UserObject, 'setattr', return_value=None) as mo:
            user1.site1 = None
            mo.assert_called_once_with('site1', None)

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_remove_signals(self):
        user1 = UserObject(pk=1, name='Mike', rating=5)
        with patch.object(UserObject, 'remove', return_value=None) as mo:
            user1.remove()
            mo.assert_called_once_with()

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_set_attr_feature(self):
        class SampleObject(models.Model):
            name = models.CharHash()
            def get_db(self):
                return db
            def set_name(self, value):
                self.setattr('name', value + 'AA')

        obj = SampleObject(1)
        obj.name = '123'
        assert obj.name == '123AA'

    def test_set_attr_feature2(self):
        class SampleObject(models.Model):
            name = models.CharHash()
            def get_db(self):
                return db
            def get_name(self):
                v = self.getattr('name')
                return v + 'OO'

        obj = SampleObject(1)
        obj.name = '123'
        assert obj.name == '123OO'

    @pytest.mark.skipif(PY2, reason="requires python3")
    def test_set_attr_feature_calls(self):
        class SampleObject(models.Model):
            name = models.CharHash()
            def get_db(self):
                return db
            def set_name(self, value):
                self.setattr('name', value + 'AA')

        with patch.object(SampleObject, 'set_name', return_value=None) as mo:
            obj = SampleObject(2)
            obj.name = '123'
            mo.assert_called_with(obj, '123')

    def test_set_attr_feature_on_init(self):
        class SampleObject(models.Model):
            name = models.CharHash()
            def get_db(self):
                return db
            def set_name(self, value):
                self.setattr('name', value + 'AA')

        obj = SampleObject(1, name='123')
        assert obj.name == '123AA'



class TestDeepAttributes(CommonHelper):
    def test_access_to_none_attribute(self):
        user1 = UserObject(1, name='User1')
        assert user1.site1 is None

    def test_exception_to_deep_attribute(self):
        user1 = UserObject(1, name='User1')
        with pytest.raises(AttributeError):
            # 'NoneType' object has no attribute 'some_child'
            k = user1.site1.some_child

    def test_deep_attribute_with_default_model(self):
        user1 = UserObject(1, name='User1')
        assert user1.site2.some_child is None


class TestAutoImport(CommonHelper):
    """
    Check case which SiteColorModel class is not loaded while SiteObject
    initialized
    """

    def test_with_deferred_import(self):
        site1 = SiteObject(1, name='example.com')

        from .other_models import SiteColorModel
        assert isinstance(site1.site_color, SiteColorModel)


class TestValidators(CommonHelper):
    def test_validator_feature(self):
        site = SiteObject(1, name='x'*32)
        with pytest.raises(ValueError):
            site.name = 'x'*33

    @pytest.mark.skipif(PY2, reason="requires python3")
    @pytest.mark.parametrize('field_type', [
        models.CharHash,
        models.CharField
    ])
    def test_validators_1(self, field_type):
        mock = MagicMock()
        class SampleObject1(models.Model):
            name = field_type(validators=[mock])

            def get_db(self):
                return db

        test_object = SampleObject1(1)
        test_object.name = 'Name'
        mock.assert_called_once_with('Name')

    @pytest.mark.skipif(PY2, reason="requires python3")
    @pytest.mark.parametrize('field_type', [
        models.IntegerField,
        models.IntegerHash
    ])
    def test_validators_2(self, field_type):
        mock = MagicMock()
        class SampleObject1(models.Model):
            value = field_type(validators=[mock])

            def get_db(self):
                return db

        test_object = SampleObject1(1, value=1234)
        mock.assert_called_once_with(1234)
