# -*- coding: utf-8 -*-

import unittest

from pyslp import parse


class TestMultiCast(unittest.TestCase):

    def test_parse_registration(self):
        data = b"\x02\x03\x00\x00R@\x00\x00\x00\x00UI\x00\x02en\x00\x00\x0f\x00\x17service:test://test.com\x00\x00\x0cservice:test\x00\x05anapa\x00\r(attr='test')\x00"
        header, url_entries, msg = parse.parse_registration(data)
        self.assertDictEqual(
            header, dict(
                version=2,
                function_id=3,
                xid=21833,
                length=82,
                language_tag_length=2,
                language_tag='en'
            )
        )
        self.assertDictEqual(
            url_entries, dict(
                lifetime=15,
                url='service:test://test.com'
            )
        )
        self.assertDictEqual(
            msg, dict(
                service_type='service:test',
                scope_list='anapa',
                attr_list="(attr='test')"
            )
        )

    def test_parse_request(self):
        data = b'\x02\x01\x00\x00* \x00\x00\x00\x00&\x0c\x00\x02en\x00\x00\x00\x0cservice:test\x00\x04test\x00\x00\x00\x00'
        header, msg = parse.parse_request(data)
        self.assertDictEqual(
            header, dict(
                version=2,
                function_id=1,
                xid=9740,
                length=42,
                language_tag_length=2,
                language_tag='en'
            )
        )
        self.assertDictEqual(
            msg, dict(
                service_type='service:test',
                scope_list='test'
            )
        )

    def test_parse_reply(self):
        data = b'\x02\x02\x00\x001\x00\x00\x00\x00\x00?\xca\x00\x02en\x00\x00\x00\x01\x00\xff\xff\x00\x17service:test://test.com\x00'
        header, error_code, url_entries = parse.parse_reply(data)
        self.assertDictEqual(
            header, dict(
                version=2,
                function_id=2,
                xid=16330,
                length=49,
                language_tag_length=2,
                language_tag='en'
            )
        )
        self.assertEqual(error_code, 0)
        self.assertEqual(len(url_entries), 1)
        self.assertDictEqual(
            url_entries[0], dict(
                lifetime=65535,
                url='service:test://test.com'
            )
        )

    def test_parse_attr_request(self):
        data = b'\x02\x06\x00\x008 \x00\x00\x00\x00\x1e\xf2\x00\x02en\x00\x00\x00\x17service:test://test.com\x00\x07DEFAULT\x00\x00\x00\x00'
        header, msg = parse.parse_attr_request(data)
        self.assertDictEqual(
            header, dict(
                version=2,
                function_id=6,
                xid=7922,
                length=56,
                language_tag_length=2,
                language_tag='en'
            )
        )
        self.assertDictEqual(
            msg, dict(
                url='service:test://test.com',
                scope_list='DEFAULT'
            )
        )

    def test_parse_attr_reply(self):
        data = b'\x02\x07\x00\x00\x1d\x00\x00\x00\x00\x00\x96\x7f\x00\x02en\x00\x00\x00\x08(attr=1)\x00'
        header, error_code, attr_list = parse.parse_attr_reply(data)
        self.assertDictEqual(
            header, dict(
                version=2,
                function_id=7,
                xid=38527,
                length=29,
                language_tag_length=2,
                language_tag='en'
            )
        )
        self.assertEqual(error_code, 0)
        self.assertEqual(attr_list, '(attr=1)')

    def test_parse_deregistration(self):
        data = b'\x02\x04\x00\x008\x00\x00\x00\x00\x00>\x0c\x00\x02en\x00\x07DEFAULT\x00\x00\x00\x00\x17service:test://test.com\x00\x00\x00'
        header, url_entry, scope_list = parse.parse_deregistration(data)
        self.assertDictEqual(
            header, dict(
                version=2,
                function_id=4,
                xid=15884,
                length=56,
                language_tag_length=2,
                language_tag='en'
            )
        )
        self.assertDictEqual(
            url_entry, dict(
                url='service:test://test.com',
                lifetime=0
            )
        )
        self.assertEqual(scope_list, 'DEFAULT')
