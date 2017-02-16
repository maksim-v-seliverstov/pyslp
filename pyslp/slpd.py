# -*- coding: utf-8 -*-

import copy
import asyncio
from datetime import datetime

from pyslp.utils import get_lst
from pyslp import parse, creator, multicast


class SLPDServer:

    def __init__(self):
        self.services = dict()
        self.url_entries = dict()
        self.lifetime = dict()

        self.flag_continue = True
        self.transports = list()
        self.ip_addrs = list()

    def connection_made(self, transport):
        self.transports.append(transport)

    @asyncio.coroutine
    def update(self, ip_addrs=list(), mcast_port=None, mcast_group=None):
        while self.flag_continue:
            urls = list()
            lifetime = copy.copy(self.lifetime)
            for url in lifetime:
                if lifetime[url] == 65535:
                    continue
                utc = datetime.strptime(self.url_entries[url]['local_ts'], "%Y-%m-%d %H:%M:%S.%f")
                delta_utc = (datetime.utcnow() - utc).total_seconds()
                if delta_utc > lifetime[url]:
                    urls.append(url)
            for url in urls:
                self.remove(url)

            for ip_addr in list(set(ip_addrs) - set(self.ip_addrs)):
                yield from multicast.create_listener(
                    lambda: Receiver(self),
                    ip_addr, mcast_port, mcast_group
                )
                self.ip_addrs.append(ip_addr)

            yield from asyncio.sleep(0.5)

    def remove(self, url):
        service_type = self.url_entries[url]['service_type']
        self.services[service_type].remove(url)
        if not self.services[service_type]:
            self.services.pop(service_type,  None)
        self.lifetime.pop(url, None)
        self.url_entries.pop(url, None)

    def datagram_received(self, data, addr):
        header, _ = parse.parse_header(data)
        if header['function_id'] == 3:
            response = creator.create_acknowledge(xid=header['xid'])

            header, url_entries, msg = parse.parse_registration(data)
            service_type = msg['service_type']
            url = url_entries['url']
            lifetime = url_entries['lifetime']

            if service_type in self.services:
                self.services[service_type].update({url})
                self.lifetime[url] = lifetime
            else:
                self.services[service_type] = {url}
                self.lifetime[url] = lifetime

            self.url_entries[url] = dict(
                attr_list=msg['attr_list'],
                local_ts=str(datetime.utcnow()),
                lifetime=lifetime,
                service_type=service_type
            )

            for transport in self.transports:
                transport.sendto(response, addr)

        elif header['function_id'] == 1:
            header, msg = parse.parse_request(data)
            service_type = msg['service_type']

            if service_type not in self.services:
                response = creator.create_reply(xid=header['xid'], url_entries=[])
                for transport in self.transports:
                    transport.sendto(response, addr)
                return

            urls = list(self.services[service_type])
            url_entries = list()
            for url in urls:
                url_entries.append(
                    dict(
                        url=url,
                        lifetime=self.lifetime[url]
                    )
                )

            response = creator.create_reply(
                xid=header['xid'],
                url_entries=url_entries
            )
            for transport in self.transports:
                transport.sendto(response, addr)

        elif header['function_id'] == 6:
            header, msg = parse.parse_attr_request(data)
            url = msg['url']

            attr_list = ''
            if url in self.url_entries:
                attr_list = self.url_entries[url]['attr_list']

            response = creator.create_attr_reply(
                xid=header['xid'],
                attr_list=attr_list
            )

            for transport in self.transports:
                transport.sendto(response, addr)

        elif header['function_id'] == 4:
            header, url_entry, scope_list = parse.parse_deregistration(data)
            response = creator.create_acknowledge(xid=header['xid'])
            url = url_entry['url']
            if url not in self.url_entries:
                return
            self.remove(url)
            for transport in self.transports:
                transport.sendto(response, addr)

    def close(self):
        self.flag_continue = False
        for transport in self.transports:
            transport.close()


class Receiver(asyncio.DatagramProtocol):

    def __init__(self, slpd):
        self.slpd = slpd

    def connection_made(self, transport):
        self.slpd.connection_made(transport)

    def datagram_received(self, data, addr):
        self.slpd.datagram_received(data, addr)


@asyncio.coroutine
def create_slpd(ip_addrs, mcast_port=427, mcast_group='239.255.255.253', loop=None):
    ip_addrs = get_lst(ip_addrs)
    slpd = SLPDServer()
    loop = loop or asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(
        slpd.update(
            ip_addrs=ip_addrs,
            mcast_port=mcast_port,
            mcast_group=mcast_group
        ),
        loop
    )
    return slpd


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    ip_addrs = '127.0.0.1'
    if ip_addrs is None:
        raise Exception('You should set ip address')
    loop.run_until_complete(create_slpd(ip_addrs))
    loop.run_forever()
