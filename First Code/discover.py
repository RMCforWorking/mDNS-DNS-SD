#!/usr/bin/env python3
"""
mdns_discover.py - Discoverer îmbunătățit
 - trimite query PTR repetat
 - afișează toate pachetele primite (summary + decoded records)
 - menține cache cu TTL
"""
import socket, struct, time, select

MCAST_GRP = "224.0.0.251"
MCAST_PORT = 5353
SERVICE_TYPE = "_monitor._udp.local."
QUERY_REPEAT = 1
TIMEOUT = 70  # secunde total

def build_name(name):
    parts = [p for p in name.split('.') if p != '']
    out = b''
    for p in parts:
        out += bytes([len(p)]) + p.encode()
    out += b'\x00'
    return out

def build_query_ptr(service_name):
    # mDNS often uses ID=0; flags=0 for query
    header = struct.pack("!HHHHHH", 0, 0, 1, 0, 0, 0)
    q = build_name(service_name) + struct.pack("!HH", 12, 1)  # PTR, class IN
    return header + q

# simple name parser that handles pointers
def parse_name(data, offset):
    labels = []
    jumped = False
    orig = offset
    while True:
        if offset >= len(data):
            return ("", offset+1)
        l = data[offset]
        if l == 0:
            offset += 1
            break
        if (l & 0xC0) == 0xC0:
            b2 = data[offset+1]
            pointer = ((l & 0x3F) << 8) | b2
            if not jumped:
                orig = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        labels.append(data[offset:offset+l].decode(errors='ignore'))
        offset += l
    name = ".".join(labels)
    if jumped:
        return name, orig
    return name, offset

def parse_rr(data, offset):
    name, offset = parse_name(data, offset)
    if offset + 10 > len(data):
        return None, offset
    typ, cls, ttl, rdlen = struct.unpack("!HHIH", data[offset:offset+10])
    offset += 10
    rdata = data[offset:offset+rdlen]
    offset += rdlen
    return {"name": name, "type": typ, "class": cls, "ttl": ttl, "rdata": rdata}, offset

def decode_txt(rdata):
    i = 0
    res = {}
    while i < len(rdata):
        ln = rdata[i]
        i += 1
        piece = rdata[i:i+ln].decode(errors='ignore')
        i += ln
        if '=' in piece:
            k,v = piece.split('=',1)
            res[k]=v
        else:
            res[piece]=''
    return res

def decode_srv(rdata):
    if len(rdata) < 6:
        return None
    priority, weight, port = struct.unpack("!HHH", rdata[:6])
    target, _ = parse_name(rdata, 6)
    return {"priority": priority, "weight": weight, "port": port, "target": target}

def discover():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass

    try:
        sock.bind(('', MCAST_PORT))
    except Exception as e:
        print("[discover] bind error:", e)
        sock.close()
        return

    # join multicast
    try:
        mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except Exception as e:
        print("[discover] IP_ADD_MEMBERSHIP:", e)

    # enable loopback to receive our own queries if necessary
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    except Exception:
        pass

    # send repeated queries
    q = build_query_ptr(SERVICE_TYPE)
    for i in range(QUERY_REPEAT):
        try:
            sock.sendto(q, (MCAST_GRP, MCAST_PORT))
            print(f"[discover] sent PTR query ({i+1}/{QUERY_REPEAT}) for {SERVICE_TYPE}")
        except Exception as e:
            print("[discover] send error:", e)
        time.sleep(0.2)

    # listen and parse
    start = time.time()
    cache = {}
    while time.time() - start < TIMEOUT:
        r, _, _ = select.select([sock], [], [], 0.5)
        if not r:
            continue
        data, addr = sock.recvfrom(9000)
        print(f"\n[discover] packet from {addr} len={len(data)}")
        if len(data) < 12:
            continue
        id, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", data[:12])
        print(f" header: flags=0x{flags:04x} qd={qdcount} an={ancount} ns={nscount} ar={arcount}")
        off = 12
        for _ in range(qdcount):
            _, off = parse_name(data, off)
            off += 4
        total_rr = ancount + nscount + arcount
        answers = []
        for _ in range(total_rr):
            rr, off = parse_rr(data, off)
            if rr is None:
                break
            answers.append(rr)
        # show summary
        for a in answers:
            tname = a['name']
            ttype = a['type']
            if ttype == 12:  # PTR
                name, _ = parse_name(a['rdata'], 0)
                print(f" PTR: {tname} -> {name} (ttl={a['ttl']})")
                # create cache entry placeholder
                cache.setdefault(name, {})['ptr_ttl'] = a['ttl']
            elif ttype == 33:  # SRV
                srv = decode_srv(a['rdata'])
                print(f" SRV: {tname} -> {srv} (ttl={a['ttl']})")
                cache.setdefault(tname, {})['srv'] = srv
            elif ttype == 16:  # TXT
                txt = decode_txt(a['rdata'])
                print(f" TXT: {tname} -> {txt} (ttl={a['ttl']})")
                cache.setdefault(tname, {})['txt'] = txt
            elif ttype == 1:  # A
                try:
                    ip = socket.inet_ntoa(a['rdata'])
                except Exception:
                    ip = None
                print(f" A: {tname} -> {ip} (ttl={a['ttl']})")
                cache.setdefault(tname, {})['a'] = ip

    print("\n[discover] final cache:")
    for k,v in cache.items():
        print(k, ":", v)
    sock.close()

if __name__ == "__main__":
    discover()
