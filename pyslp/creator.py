# -*- coding: utf-8 -*-

import uuid


def create_header(function_id, data_length, ofr, version=2, xid=None, language_tag='en'):
    header = b''
    for b in [version, function_id]:
        header += bytes([b])

    language_tag_length = len(language_tag.encode())

    header += (14 + language_tag_length + data_length).to_bytes(3, byteorder='big')

    u = uuid.uuid1()
    for b in [ofr, 0, 0, 0, 0]:
        header += bytes([b])

    if xid is None:
        for b in [u.clock_seq_hi_variant, u.clock_seq_low]:
            header += bytes([b])
    else:
        header += xid.to_bytes(2, byteorder='big')

    header += language_tag_length.to_bytes(2, byteorder='big')
    header += language_tag.encode()

    return header


def create_acknowledge(xid, error_code=0):
    data = error_code.to_bytes(length=2, byteorder='big')
    header = create_header(function_id=5, data_length=len(data), xid=xid, ofr=0)
    return header + data


def create_url_entry(lifetime, url):
    data = bytes([0])
    data += lifetime.to_bytes(length=2, byteorder='big')
    data += (len(url.encode())).to_bytes(length=2, byteorder='big')
    data += url.encode()
    data += bytes([0])
    return data


def create_reply(xid, url_entries, error_code=0):
    data = error_code.to_bytes(length=2, byteorder='big')
    data += len(url_entries).to_bytes(length=2, byteorder='big')
    for entry in url_entries:
        data += create_url_entry(**entry)
    header = create_header(function_id=2, data_length=len(data), xid=xid, ofr=0)
    return header + data


def create_registration(service_type, scope_list, attr_list, lifetime, url):
    data = create_url_entry(lifetime, url)

    for value in [service_type, scope_list, attr_list]:
        value_length = len(value.encode()).to_bytes(length=2, byteorder='big')
        data += value_length
        data += value.encode()

    data += bytes([0])

    header = create_header(function_id=3, data_length=len(data), ofr=64)
    return header + data


def create_request(service_type, scope_list='DEFAULT'):
    data = b''
    for value in ['', service_type, scope_list, '', '']:
        value_length = len(value.encode()).to_bytes(length=2, byteorder='big')
        data += value_length
        data += value.encode()

    header = create_header(function_id=1, data_length=len(data), ofr=64)
    return header + data


def create_attr_request(url, scope_list='DEFAULT'):
    data = b''
    for value in ['', url, scope_list, '', '']:
        value_length = len(value.encode()).to_bytes(length=2, byteorder='big')
        data += value_length
        data += value.encode()

    header = create_header(function_id=6, data_length=len(data), ofr=62)
    return header + data


def create_attr_reply(xid, attr_list, error_code=0):
    data = error_code.to_bytes(length=2, byteorder='big')
    data += len(attr_list).to_bytes(length=2, byteorder='big')
    data += attr_list.encode()
    data += bytes([0])

    header = create_header(function_id=7, data_length=len(data), xid=xid, ofr=0)
    return header + data


def create_deregistration(url, scope_list='DEFAULT'):
    data = b''
    for value in [scope_list]:
        value_length = len(value.encode()).to_bytes(length=2, byteorder='big')
        data += value_length
        data += value.encode()

    data += create_url_entry(lifetime=0, url=url)
    data += bytes([0])
    data += bytes([0])

    header = create_header(function_id=4, data_length=len(data), ofr=0)
    return header + data
