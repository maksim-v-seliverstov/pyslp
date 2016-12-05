# -*- coding: utf-8 -*-

import socket
import struct
import asyncio


@asyncio.coroutine
def create_listener(protocol_factory, ip_addr, port, group, loop=None):
    loop = loop or asyncio.get_event_loop()
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    transport, protocol = yield from loop.create_datagram_endpoint(protocol_factory, sock=sock)

    mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton(ip_addr))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    return transport


@asyncio.coroutine
def create_sender(protocol_factory, ip_addr, port, loop=None):
    loop = loop or asyncio.get_event_loop()
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind((ip_addr, port))

    try:
        transport, protocol = yield from loop.create_datagram_endpoint(protocol_factory, sock=sock)
    except:
        sock.close()
        raise

    try:
        sock = transport if isinstance(transport, socket.socket) else transport.get_extra_info('socket')
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip_addr))
    except:
        transport.close()
        raise

    return transport
