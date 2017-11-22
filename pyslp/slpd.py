# -*- coding: utf-8 -*-

import copy
import asyncio
from datetime import datetime

from pyslp.utils import get_lst
from pyslp import parse, creator, multicast


class SLPDServer:

    def __init__(self, scope='DEFAULT'):
        self.services = dict()
        self.url_entries = dict()
        self.lifetime = dict()

        self.flag_continue = True
        self.transports = list()
        self.ip_addrs = list()

        self.scope = scope

    def connection_made(self, transport):
        self.transports.append(transport)

    @asyncio.coroutine
    def update(self, ip_addrs=list(), mcast_port=None, mcast_group=None):
        while self.flag_continue:
            for interface in self.ip_addrs:
                urls = list()
                lifetime = copy.copy(self.lifetime[interface])
                for url in lifetime:
                    if lifetime[url] == 65535:
                        continue
                    utc = datetime.strptime(self.url_entries[interface][url]['local_ts'], "%Y-%m-%d %H:%M:%S.%f")
                    delta_utc = (datetime.utcnow() - utc).total_seconds()
                    if delta_utc > lifetime[url]:
                        urls.append(url)
                for url in urls:
                    self.remove(interface, url)

            for ip_addr in list(set(ip_addrs) - set(self.ip_addrs)):
                yield from multicast.create_listener(
                    lambda: Receiver(self, ip_addr),
                    ip_addr, mcast_port, mcast_group
                )
                self.ip_addrs.append(ip_addr)

                self.services[ip_addr] = dict()
                self.url_entries[ip_addr] = dict()
                self.lifetime[ip_addr] = dict()

            yield from asyncio.sleep(0.5)

    def remove(self, interface, url):
        service_type = self.url_entries[interface][url]['service_type']
        self.services[interface][service_type].remove(url)
        if not self.services[interface][service_type]:
            self.services[interface].pop(service_type,  None)
        self.lifetime[interface].pop(url, None)
        self.url_entries[interface].pop(url, None)

    def datagram_received(self, data, addr, interface, transport):
        header, _ = parse.parse_header(data)
        if header['function_id'] == 3:
            response = creator.create_acknowledge(xid=header['xid'])

            header, url_entries, msg = parse.parse_registration(data)

            if msg['scope_list'] != self.scope:
                return

            service_type = msg['service_type']
            url = url_entries['url']
            lifetime = url_entries['lifetime']

            if service_type in self.services[interface]:
                self.services[interface][service_type].update({url})
                self.lifetime[interface][url] = lifetime
            else:
                self.services[interface][service_type] = {url}
                self.lifetime[interface][url] = lifetime

            self.url_entries[interface][url] = dict(
                attr_list=msg['attr_list'],
                local_ts=str(datetime.utcnow()),
                lifetime=lifetime,
                service_type=service_type
            )

            transport.sendto(response, addr)

        elif header['function_id'] == 1:
            header, msg = parse.parse_request(data)

            if msg['scope_list'] != self.scope:
                return

            service_type = msg['service_type']

            if service_type not in self.services[interface]:
                response = creator.create_reply(xid=header['xid'], url_entries=[])
                transport.sendto(response, addr)
                return

            urls = list(self.services[interface][service_type])
            url_entries = list()
            for url in urls:
                url_entries.append(
                    dict(
                        url=url,
                        lifetime=self.lifetime[interface][url]
                    )
                )

            response = creator.create_reply(
                xid=header['xid'],
                url_entries=url_entries
            )
            transport.sendto(response, addr)

        elif header['function_id'] == 6:
            header, msg = parse.parse_attr_request(data)

            if msg['scope_list'] != self.scope:
                return

            url = msg['url']

            attr_list = ''
            if url in self.url_entries[interface]:
                attr_list = self.url_entries[interface][url]['attr_list']

            response = creator.create_attr_reply(
                xid=header['xid'],
                attr_list=attr_list
            )

            transport.sendto(response, addr)

        elif header['function_id'] == 4:
            header, url_entry, scope_list = parse.parse_deregistration(data)

            if scope_list != self.scope:
                return

            response = creator.create_acknowledge(xid=header['xid'])
            url = url_entry['url']
            if url not in self.url_entries[interface]:
                transport.sendto(response, addr)
                return
            self.remove(interface, url)
            transport.sendto(response, addr)

    def close(self):
        self.flag_continue = False
        for transport in self.transports:
            transport.close()


class Receiver(asyncio.DatagramProtocol):

    def __init__(self, slpd, ip_addr):
        self.slpd = slpd
        self.ip_addr = ip_addr
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.slpd.connection_made(transport)

    def datagram_received(self, data, addr):
        self.slpd.datagram_received(data, addr, self.ip_addr, self.transport)


@asyncio.coroutine
def create_slpd(ip_addrs, mcast_port=427, mcast_group='239.255.255.253', loop=None, scope='DEFAULT'):
    ip_addrs = get_lst(ip_addrs)
    slpd = SLPDServer(scope=scope)
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
    ip_addrs = ['127.0.0.1']
    if ip_addrs is None:
        raise Exception('You should set ip address')
    loop.run_until_complete(create_slpd(ip_addrs))
    loop.run_forever()
