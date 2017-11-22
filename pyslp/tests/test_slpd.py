# -*- coding: utf-8 -*-

import asyncio
import unittest

from pyslp.slpd import create_slpd
from pyslp.slptool import SLPClient


class TestSLPD(unittest.TestCase):

    loop = asyncio.get_event_loop()

    def setUp(self):
        self.ip_addr = ['127.0.0.1', '127.0.0.2']
        self.mcast_group = '239.255.255.253'
        self.mcast_port = 427
        self.service_type = 'service:seliverstov'

        self.event = asyncio.Event()

        self.transport = self.loop.run_until_complete(create_slpd(ip_addrs=self.ip_addr))
        self.slp_client = SLPClient(ip_addrs=self.ip_addr)

    def tearDown(self):
        self.transport.close()
        self.loop.run_until_complete(asyncio.sleep(1))

    def assertService(self, service_type, urls):
        find_urls = self.loop.run_until_complete(
            self.slp_client.findsrvs(service_type=service_type)
        )
        self.assertSetEqual(set(urls), set(find_urls[0][0]))

    def test_register_and_deregister(self):
        self.loop.run_until_complete(asyncio.sleep(1))
        self.assertService(self.service_type, [])
        result = list()
        urls = ['{}://test_{}.com'.format(self.service_type, i) for i in range(3)]
        for url in urls:
            self.loop.run_until_complete(
                self.slp_client.register(
                    service_type=self.service_type,
                    url=url
                )
            )
            result.append(url)
            self.assertService(self.service_type, result)

        for url in urls:
            self.loop.run_until_complete(
                self.slp_client.deregister(
                    url=url
                )
            )
            result.remove(url)
            self.assertService(self.service_type, result)

        self.assertService(self.service_type, [])

    def test_findattrs(self):
        self.loop.run_until_complete(asyncio.sleep(1))
        url = '{}://test.com'.format(self.service_type)
        attr_list = '(attr1=value1),(attr2=value2)'
        self.loop.run_until_complete(
            self.slp_client.register(
                service_type=self.service_type,
                url=url,
                attr_list=attr_list
            )
        )
        self.assertService(self.service_type, [url])
        find_attr_list = self.loop.run_until_complete(
            self.slp_client.findattrs(url=url)
        )
        self.assertEqual(attr_list, find_attr_list)
