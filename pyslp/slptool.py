# -*- coding: utf-8 -*-

import asyncio
from concurrent.futures import FIRST_COMPLETED, ALL_COMPLETED

from pyslp.utils import get_lst
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
            self.result.update(
                dict(
                    error_code=error_code,
                    url_entries=url_entries
                )
            )
        elif header['function_id'] == 5:
            _, error_code = parse.parse_acknowledge(data)
            self.result.update(
                dict(
                    error_code=error_code
                )
            )
        elif header['function_id'] == 7:
            _, error_code, attr_list = parse.parse_attr_reply(data)
            self.result.update(
                dict(
                    error_code=error_code,
                    attr_list=attr_list
                )
            )

        self.event.set()


class SLPClient:

    def __init__(self, ip_addrs, mcast_group='239.255.255.253', mcast_port=427, loop=None, scope='DEFAULT'):
        self.ip_addrs = get_lst(ip_addrs)
        self.mcast_group = mcast_group
        self.mcast_port = mcast_port
        self.scope = scope

        self.loop = loop or asyncio.get_event_loop()

    @asyncio.coroutine
    def _send(self, ip_addr, data):
        mcast_transport = yield from multicast.create_sender(
            asyncio.DatagramProtocol, ip_addr, 0
        )
        try:
            event = asyncio.Event()
            result = dict()
            transport, _ = yield from self.loop.create_datagram_endpoint(
                lambda: Receiver(event, result), sock=mcast_transport._sock
            )
            mcast_transport.sendto(data, (self.mcast_group, self.mcast_port))
            try:
                done, pending = yield from asyncio.wait([event.wait()], timeout=1, return_when=FIRST_COMPLETED)
                for f in pending:
                    f.cancel()
                if not (done or result):
                    raise SLPClientError('Internal error')
                transport.close()
                return result
            finally:
                transport.close()
        finally:
            mcast_transport.close()

    @asyncio.coroutine
    def _wait(self, fs):
        flag_completed = False

        timeout = 5
        while not flag_completed:
            done, pending = yield from asyncio.wait(fs, timeout=timeout, return_when=ALL_COMPLETED)

            if not done:
                for f in pending:
                    f.cancel()
                raise SLPClientError('Internal error')

            for f in done:
                try:
                    result = f.result()
                    error_code = result['error_code']
                    if error_code == 0:
                        flag_completed = True
                        break
                except:
                    pass

            timeout /= 2

            if flag_completed:
                break

            if pending:
                fs = list(pending)
            else:
                try:
                    result = done.pop().result()  # raise exception
                    if not pending:
                        raise SLPClientError('SLP error code: {}'.format(error_code))
                except:
                    raise SLPClientError('SLP error code: {}'.format(error_code))

        return result

    def send(self, data, ip_addr=None):
        fs = list()
        if ip_addr is not None:
            fs.append(self._send(ip_addr, data))
        else:
            for ip_addr in self.ip_addrs:
                fs.append(self._send(ip_addr, data))

        return (yield from self._wait(fs))

    @asyncio.coroutine
    def register(self, service_type, url, attr_list='', lifetime=65535):
        data = creator.create_registration(
            service_type=service_type,
            scope_list=self.scope,
            attr_list=attr_list,
            lifetime=lifetime,
            url=url
        )
        yield from self.send(data)

    @asyncio.coroutine
    def deregister(self, url):
        data = creator.create_deregistration(url=url, scope_list=self.scope)
        yield from self.send(data)

    @asyncio.coroutine
    def findsrvs(self, service_type):
        data = creator.create_request(
            service_type=service_type,
            scope_list=self.scope
        )
        url_entries = list()

        addrs = list()
        for ip_addr in self.ip_addrs:
            try:
                result = yield from self.send(data, ip_addr)
            except:
                continue
            url_entries.append([entry['url'] for entry in result['url_entries']])
            addrs.append(ip_addr)
        if not url_entries:
            raise SLPClientError('Internal error')
        return url_entries, addrs

    @asyncio.coroutine
    def findattrs(self, url, ip_addrs=None):
        data = creator.create_attr_request(
            url=url,
            scope_list=self.scope
        )
        if ip_addrs is None:
            addrs = self.ip_addrs
        else:
            addrs = ip_addrs

        flag_error = False

        for ip_addr in addrs:
            try:
                result = yield from self.send(data, ip_addr)
                if result['attr_list'] != '':
                    return result['attr_list']
            except:
                flag_error = True

        if flag_error:
            raise SLPClientError('Internal erro: {}'.format(ip_addrs))

        return list()

if __name__ == '__main__':
    for _ in range(10):
        loop = asyncio.get_event_loop()
        ip_addrs = '127.0.0.1'
        if ip_addrs is None:
            raise Exception('You should set ip address')
        slp_client = SLPClient(ip_addrs=ip_addrs)
        service_type = 'service:test'
        for url in ['service:test://test.com', 'service:test://test_1.com']:
            loop.run_until_complete(
                slp_client.register(
                    service_type=service_type,
                    lifetime=15,
                    url=url,
                    attr_list=''
                )
            )
            print('{} - service is registered successfully'.format(url))
        url_entries = loop.run_until_complete(
            slp_client.findsrvs(service_type=service_type)
        )
        print(url_entries)
        print('findsrvs for {} - {}'.format(service_type, url_entries))
        for _url_entries in url_entries[0]:
            for url in _url_entries:
                attr_list = loop.run_until_complete(
                    slp_client.findattrs(url=url)
                )
                print('findattrs for {} - {}'.format(url, attr_list))
                loop.run_until_complete(
                    slp_client.deregister(url=url)
                )
                print('{} - service is deregistered successfully'.format(url))
