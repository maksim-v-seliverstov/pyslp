# -*- coding: utf-8 -*-

import asyncio

from pyslp import multicast, creator, parse


class SLPClientError(Exception):
    pass


class Receiver(asyncio.DatagramProtocol):

    def __init__(self, event=None, result=None):
        self.event = event
        self.result = result

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        header, _ = parse.parse_header(data)
        if header['function_id'] == 2:
            _, error_code, url_entries = parse.parse_reply(data)
            self.result[2] = dict(
                error_code=error_code,
                url_entries=url_entries
            )
        elif header['function_id'] == 5:
            _, error_code = parse.parse_acknowledge(data)
            self.result[5] = dict(
                error_code=error_code
            )
        elif header['function_id'] == 7:
            _, error_code, attr_list = parse.parse_attr_reply(data)
            self.result[7] = dict(
                error_code=error_code,
                attr_list=attr_list
            )

        self.event.set()


class SLPClient:
    def __init__(self, ip_addr, mcast_group='239.255.255.253', mcast_port=427, loop=None):
        self.ip_addr = ip_addr
        self.mcast_group = mcast_group
        self.mcast_port = mcast_port

        self.loop = loop or asyncio.get_event_loop()

    @asyncio.coroutine
    def send(self, data):
        mcast_transport = yield from multicast.create_sender(
            asyncio.DatagramProtocol, self.ip_addr, 0
        )
        try:
            mcast_transport.sendto(data, (self.mcast_group, self.mcast_port))

            event = asyncio.Event()
            result = dict()
            transport, _ = yield from self.loop.create_datagram_endpoint(
                lambda: Receiver(event, result), sock=mcast_transport._sock
            )
            try:
                asyncio.wait([event.wait()], timeout=5)
                done, pending = yield from asyncio.wait([event.wait()], timeout=5)
                if not (done or result):
                    raise SLPClientError('Internal error')
                transport.close()
                return result
            finally:
                transport.close()
        finally:
            mcast_transport.close()

    @asyncio.coroutine
    def register(self, service_type, url, scope_list='DEFAULT', attr_list='', lifetime=15):
        data = creator.create_registration(
            service_type=service_type,
            scope_list=scope_list,
            attr_list=attr_list,
            lifetime=lifetime,
            url=url
        )

        result = yield from self.send(data)
        error_code = result[5]['error_code']
        if error_code != 0:
            raise SLPClientError('SLP error code: {}'.format(error_code))

    @asyncio.coroutine
    def deregister(self, url):
        data = creator.create_deregistration(
            url=url
        )

        result = yield from self.send(data)
        error_code = result[5]['error_code']
        if error_code != 0:
            raise SLPClientError('SLP error code: {}'.format(error_code))

    @asyncio.coroutine
    def findsrvs(self, service_type, scope_list='DEFAULT'):
        data = creator.create_request(
            service_type=service_type,
            scope_list=scope_list
        )

        result = yield from self.send(data)
        error_code = result[2]['error_code']
        if error_code != 0:
            raise SLPClientError('SLP error code: {}'.format(error_code))

        return [entry['url'] for entry in result[2]['url_entries']]

    @asyncio.coroutine
    def findattrs(self, url, scope_list='DEFAULT'):
        data = creator.create_attr_request(
            url=url,
            scope_list=scope_list
        )

        result = yield from self.send(data)
        error_code = result[7]['error_code']
        if error_code != 0:
            raise SLPClientError('SLP error code: {}'.format(error_code))

        return result[7]['attr_list']


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    ip_addr = None
    if ip_addr is None:
        raise Exception('You should set ip address')
    slp_client = SLPClient(ip_addr=ip_addr)
    service_type = 'service:test'
    for url in ['service:test://test.com', 'service:test://test_1.com']:
        loop.run_until_complete(
            slp_client.register(
                service_type=service_type,
                lifetime=15,
                url=url,
                attr_list="(attr=1)"
            )
        )
        print('{} - service is registered successfully'.format(url))
    url_entries = loop.run_until_complete(
        slp_client.findsrvs(service_type=service_type)
    )
    print('findsrvs for {} - {}'.format(service_type, url_entries))
    for url in url_entries:
        attr_list = loop.run_until_complete(
            slp_client.findattrs(url=url)
        )
        print('findattrs for {} - {}'.format(url, attr_list))
        loop.run_until_complete(
            slp_client.deregister(url=url)
        )
        print('{} - service is deregistered successfully'.format(url))
