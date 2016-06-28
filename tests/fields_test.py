import datetime as dt
import sys
import pytest
import redis
from astra import models
from .sample_model import UserObject, SiteObject, ParentExample, ChildExample

PY_2 = sys.version_info[0] == 2
if not PY_2:
    from unittest.mock import MagicMock


# Patch redis. Connection method for collect command sequences for this test
def patched_send_command(self, *args):
    if 'commands' in globals():
        commands.append(args)  # commands.append(' '.join(args))
    self.send_packed_command(self.pack_command(*args))


redis.Connection.send_command = patched_send_command


# Common class for simplify testing
class CommonHelper:
    def setup(self):
        global db, commands
        db = redis.StrictRedis(host='127.0.0.1', decode_responses=True)
        UserObject.database = db
        SiteObject.database = db
        ParentExample.database = db
        db.flushall()
        commands = []

    def setup_method(self, test_method):
        pass

    def teardown_method(self, test_method):
        pass

    # Helpers
    def assert_commands_count(self, count):
        assert len(commands) == count, commands

    def assert_keys_count(self, count):
        assert len(db.keys()) == count


# Test of base fields behavior
class TestModelField(CommonHelper):
    def test_set_and_read_attrs(self):
        user1 = UserObject(1)
        user1.name = 'Username'
        assert user1.name == 'Username'
        user1.name = 12345
        assert user1.name == 12345
        self.assert_commands_count(3)

    def test_remove_element(self):
        user1 = UserObject(1)
        user1.name = 'Username'
        user1.remove()
        self.assert_keys_count(0)

    def test_set_attrs_via_kwargs(self):
        user1 = UserObject(1, name='Username')
        assert user1.name == 'Username'

        user2 = UserObject(name='Username', pk=2)
        assert user2.name == 'Username'

    def test_non_existing_object_default_value(self):
        user_read = UserObject(1)
        assert user_read.name is None
        self.assert_commands_count(1)

    def test_default_values(self):
        user1 = UserObject(1)
        assert user1.name is None
        assert user1.name != ''
        assert user1.is_admin is False
        assert user1.is_admin is not True
        # assert user1.is_admin is None  # TODO: somehow problems with this it

    @pytest.mark.skipif(PY_2, reason="requires python3")
    def test_redis_pass_arg_directly(self):
        db.hset = MagicMock()
        user1 = UserObject(1)
        user1.login = 1234
        # redis independently convert key to string
        db.hset.assert_called_once_with('astra::userobject::hash::1',
                                        'login', 1234)

    @pytest.mark.skipif(PY_2, reason="requires python3")
    def test_custom_prefix_for_redis_model(self):
        db.hset = MagicMock()
        site1 = SiteObject(5)
        site1.name = 'Site1'
        db.hset.assert_called_once_with(
            'custom_prefix::siteobject::hash::5', 'name', 'Site1')

    def test_success_saved(self):
        user_write = UserObject(1)
        user_write.name = 'Username'
        user_write.login = 'user@null.com'

        user_read = UserObject(1)
        assert user_read.name == 'Username'
        assert user_read.login == 'user@null.com'
        self.assert_commands_count(3)

    @pytest.mark.skipif(PY_2, reason="requires python3")
    def test_read_real_value(self):
        db.hgetall = MagicMock(return_value={'name': 'Username'})
        user1 = UserObject(1)
        assert user1.name == 'Username'
        assert user1.login is None

        # About Mock: https://docs.python.org/dev/library/unittest.mock.html
        # db.execute_command = MagicMock(return_value=3)
        # db.execute_command.assert_has_calls(1)

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


class TestIntegerHash(CommonHelper):
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
        assert user1_read.rating == 5  # convert to user type


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


class TestHashDelete(CommonHelper):
    def test_deleted_operations_count(self):
        class SampleObject1(models.Model):
            name = models.CharHash()
            rating = models.IntegerHash()
            field1 = models.CharField()
        SampleObject1.database = db
        test_object = SampleObject1(1, name='Alice', rating=22, field1='test')
        self.assert_commands_count(3)  # two times set hash + field
        test_object.remove()
        self.assert_commands_count(5)  # one time delete entire hash + field


class TestDateHash(CommonHelper):
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
                field = models.EnumHash(enum=('',))

        with pytest.raises(ValueError):
            class SampleObject3(models.Model):
                field = models.EnumHash(enum=(123, '43'))

    def test_save_not_enum_value(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.status = 'INVALID_ENUM'

    def test_save_correct_enum_value(self):
        user1 = UserObject(1)
        user1.status = UserObject.status_choice[1]  # ACTIVATED
        user1_read = UserObject(1)
        assert user1_read.status == UserObject.status_choice[1]


class TestLinkHash(CommonHelper):
    def test_invalid_model_define_exception(self):
        with pytest.raises(AttributeError):
            class SampleObject1(models.Model):
                user = models.ForeignKeyHash(to=123)

        with pytest.raises(AttributeError):
            class SampleObject2(models.Model):
                user = models.ForeignKeyHash(to=CommonHelper)

    def test_save_invalid_value(self):
        user1 = UserObject(1)
        with pytest.raises(ValueError):
            user1.inviter = False  # Boolean not converted to str

    def test_save_valid_value_as_int(self):
        user1 = UserObject(1, name='Username')
        user2 = UserObject(2)
        user2.inviter = 1
        self.assert_commands_count(2)

        user_reader2 = UserObject(2)
        assert isinstance(user_reader2.inviter, UserObject)
        self.assert_commands_count(3)

        assert user_reader2.inviter.pk == user1.pk
        self.assert_commands_count(3)

    def test_save_valid_value_as_instance_of_model(self):
        user1 = UserObject(1, name='Username')
        user2 = UserObject(2)
        user2.inviter = user1
        user_reader2 = UserObject(2)
        assert isinstance(user_reader2.inviter, UserObject)
        assert user_reader2.inviter.pk == user1.pk

    def test_delete_existing_value_with_none(self):
        user1 = UserObject(1, name='Username')
        user2 = UserObject(2)
        user2.inviter = user1
        user_reader2 = UserObject(2)
        assert user_reader2.inviter.pk == user1.pk
        user2_modifier = UserObject(2)
        user2_modifier.inviter = None
        user_reader2 = UserObject(2)
        assert user_reader2.inviter is None


class TestLinkField(CommonHelper):
    def test_save_valid_value_as_int(self):
        site1 = SiteObject(1, name='redis.io')
        UserObject(1, name='Username', site_id=site1)

        user_reader1 = UserObject(1)
        assert user_reader1.site_id.pk == '1'
        assert isinstance(user_reader1.site_id, SiteObject)


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
