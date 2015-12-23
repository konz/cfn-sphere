import textwrap
import unittest2
from mock import patch, Mock
from datetime import datetime
from cfn_sphere import util
from cfn_sphere.exceptions import CfnSphereException
from boto.exception import BotoServerError


class StackConfigTests(unittest2.TestCase):
    def test_convert_yaml_to_json_string_returns_valid_json_string(self):
        data = textwrap.dedent("""
        foo:
          foo: baa
        """)

        self.assertEqual('{\n  "foo": {\n    "foo": "baa"\n  }\n}', util.convert_yaml_to_json_string(data))

    def test_convert_yaml_to_json_string_returns_valid_json_string_on_empty_string_input(self):
        data = ""
        self.assertEqual('{}', util.convert_yaml_to_json_string(data))

    def test_convert_json_to_yaml_string_returns_valid_yaml_string(self):
        data = textwrap.dedent("""
        {
            "foo": {
                "foo": "baa"
            }
        }
        """)

        self.assertEqual('foo:\n  foo: baa\n', util.convert_json_to_yaml_string(data))

    def test_convert_json_to_yaml_string_returns_empty_string_on_empty_json_input(self):
        data = {}
        self.assertEqual('', util.convert_json_to_yaml_string(data))

    @patch("cfn_sphere.util.urllib2.urlopen")
    def test_get_cfn_api_server_time_returns_gmt_datetime(self, urlopen_mock):
        urlopen_mock.return_value.info.return_value.get.return_value = "Mon, 21 Sep 2015 17:17:26 GMT"
        expected_timestamp = datetime(year=2015, month=9, day=21, hour=17, minute=17, second=26)
        self.assertEqual(expected_timestamp, util.get_cfn_api_server_time())

    @patch("cfn_sphere.util.urllib2.urlopen")
    def test_get_cfn_api_server_time_raises_exception_on_empty_date_header(self, urlopen_mock):
        urlopen_mock.return_value.info.return_value.get.return_value = ""
        with self.assertRaises(CfnSphereException):
            util.get_cfn_api_server_time()

    def test_with_boto_retry_retries_method_call_for_throttling_exception(self):
        count_func = Mock()

        @util.with_boto_retry(max_retries=1, pause_time_multiplier=1)
        def my_retried_method(count_func):
            count_func()
            exception = BotoServerError("400", "error")
            exception.code = 'Throttling'
            raise exception

        with self.assertRaises(BotoServerError):
            my_retried_method(count_func)

        self.assertEqual(2, count_func.call_count)

    def test_with_boto_retry_does_not_retry_for_simple_exception(self):
        count_func = Mock()

        @util.with_boto_retry(max_retries=1, pause_time_multiplier=1)
        def my_retried_method(count_func):
            count_func()
            raise Exception

        with self.assertRaises(Exception):
            my_retried_method(count_func)

        self.assertEqual(1, count_func.call_count)

    def test_with_boto_retry_does_not_retry_for_another_boto_server_error(self):
        count_func = Mock()

        @util.with_boto_retry(max_retries=1, pause_time_multiplier=1)
        def my_retried_method(count_func):
            count_func()
            exception = BotoServerError("400", "error")
            exception.code = 'ValidationError'
            raise exception

        with self.assertRaises(BotoServerError):
            my_retried_method(count_func)

        self.assertEqual(1, count_func.call_count)

    def test_with_boto_retry_does_not_retry_without_exception(self):
        count_func = Mock()

        @util.with_boto_retry(max_retries=1, pause_time_multiplier=1)
        def my_retried_method(count_func):
            count_func()
            return "foo"

        self.assertEqual("foo", my_retried_method(count_func))
        self.assertEqual(1, count_func.call_count)
