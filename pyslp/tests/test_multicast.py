# -*- coding: utf-8 -*-

import uuid
import asyncio
import unittest


from pyslp.multicast import create_listener, create_sender


class TestReceiver(asyncio.DatagramProtocol):

    def __init__(self, data_info, event):
        self.data_info = data_info
        self.event = event

    def datagram_received(self, data, addr):
        self.data_info.append(
            dict(
                data=data,
                addr=addr
            )
        )
        self.event.set()


class TestMultiCast(unittest.TestCase):
    loop = asyncio.get_event_loop()

    def setUp(self):
        self.ip_addr = '127.0.0.1'
        self.mcast_group = '239.255.255.253'

    def test_multicast(self):
        event = asyncio.Event()
        data_info = list()

        transport = self.loop.run_until_complete(
            create_listener(
                lambda: TestReceiver(data_info, event),
                self.ip_addr, 0,
                self.mcast_group
            )
        )
        port = transport._sock.getsockname()[1]

        transport = self.loop.run_until_complete(
            create_sender(
                asyncio.DatagramProtocol,
                self.ip_addr, 0,
            )
        )

        self.assertEqual(0, len(data_info))
        data = str(uuid.uuid1()).encode()
        transport.sendto(data, (self.mcast_group, port))

        done, _ = self.loop.run_until_complete(asyncio.wait([event.wait()], timeout=1))
        self.assertEqual(1, len(done))
        self.assertEqual(1, len(data_info))
        self.assertEqual(data, data_info[0]['data'])
