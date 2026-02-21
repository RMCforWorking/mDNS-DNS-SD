#!/usr/bin/env python3
"""
mdns_advertise.py
Advertiser mDNS/DNS-SD care:
 - se leagă pe port 5353 (UDP)
 - face join la multicast 224.0.0.251
 - trimite anunțuri periodice (unsolicited)
 - ascultă query-uri și răspunde când găsește întrebarea pentru SERVICE_TYPE
 - afișează log detaliat pentru debugging

CONFIG la începutul fișierului.
"""
import random
import socket, struct, time, threading, sys
import subprocess



# ========== CONFIG ==========
SERVICE_NAME = "RamMon"
HOSTNAME = "rammon.local"
SERVICE_PORT = 8080
TTL = 200
MCAST_GRP = "224.0.0.251"
MCAST_PORT = 5353
SERVICE_TYPE = "_monitor._udp.local."
INSTANCE_SUFFIX = "._monitor._udp.local."
REANNOUNCE_INTERVAL = max(1, TTL // 3)
# ============================

def build_name(name):
    parts = [p for p in name.split('.') if p != '']
    out = b''
    for p in parts:
        out += bytes([len(p)]) + p.encode()
    out += b'\x00'
    return out

def build_ptr_record(instance_name, ttl):
    name = build_name(SERVICE_TYPE)
    typ = 12  # PTR
    cls = 1
    rdata = build_name(instance_name)
    rdlen = len(rdata)
    return name + struct.pack("!HHIH", typ, cls, ttl, rdlen) + rdata

def build_srv_record(instance_full, target_hostname, port, ttl):
    name = build_name(instance_full)
    typ = 33
    cls = 1
    priority = 0
    weight = 0
    rdata = struct.pack("!HHH", priority, weight, port) + build_name(target_hostname)
    rdlen = len(rdata)
    return name + struct.pack("!HHIH", typ, cls, ttl, rdlen) + rdata

def build_txt_record(instance_full, txt_dict, ttl):
    name = build_name(instance_full)
    typ = 16
    cls = 1
    rdata = b''
    for k,v in txt_dict.items():
        s = f"{k}={v}".encode()
        if len(s) > 255:
            s = s[:255]
        rdata += bytes([len(s)]) + s
    rdlen = len(rdata)
    return name + struct.pack("!HHIH", typ, cls, ttl, rdlen) + rdata

def build_a_record(hostname, ip, ttl):
    name = build_name(hostname)
    typ = 1
    cls = 1
    try:
        rdata = socket.inet_aton(ip)
    except Exception:
        rdata = socket.inet_aton("127.0.0.1")
    rdlen = len(rdata)
    return name + struct.pack("!HHIH", typ, cls, ttl, rdlen) + rdata

def build_mdns_response(instance_full, hostname, ip, port, txt_dict, ttl):
    # ID=0 for mDNS is common; flags=0x8400 (response + authoritative)
    header = struct.pack("!HHHHHH", 0, 0x8400, 0, 4, 0, 0)
    body = b''
    body += build_ptr_record(instance_full, ttl)
    body += build_srv_record(instance_full, hostname, port, ttl)
    body += build_txt_record(instance_full, txt_dict, ttl)
    body += build_a_record(hostname, ip, ttl)
    return header + body

def get_local_ip(dest_ip='8.8.8.8'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((dest_ip, 53))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def advertiser():
    instance_full = f"{SERVICE_NAME}{INSTANCE_SUFFIX}"
    hostname = HOSTNAME if HOSTNAME.endswith('.local') else HOSTNAME + '.local'
    ip = get_local_ip()
    port = SERVICE_PORT
    ttl = TTL

    print(f"[advertiser] instance={instance_full} hostname={hostname} ip={ip} port={port} ttl={ttl}")
    txt = {"ram": "0%"}

    # socket for both sending and receiving
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass

    # bind to mDNS port for both sending and receiving
    try:
        sock.bind(('', MCAST_PORT))
    except Exception as e:
        print("[advertiser] bind error:", e)
        sock.close()
        return

    # join multicast group
    try:
        mreq = struct.pack("=4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton("0.0.0.0"))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except Exception as e:
        # fallback variant
        try:
            mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception as e2:
            print("[advertiser] IP_ADD_MEMBERSHIP error:", e, e2)

    # ensure loopback so we receive our own multicast (helps debugging on same host)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    except Exception:
        pass

    # set multicast TTL (link-local)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))
    except Exception:
        pass

    # thread to update txt (simulate or replace with real monitor)
    def update_values():
        while True:
            txt["ram"] = f"{round(random.random()*100.0,2)}%"
            time.sleep(5)
    threading.Thread(target=update_values, daemon=True).start()

    # function to send response
    def send_response():
        resp = build_mdns_response(instance_full, hostname, ip, port, txt, ttl)
        try:
            sock.sendto(resp, (MCAST_GRP, MCAST_PORT))
            print(f"[advertiser] sent announcement ({len(resp)} bytes) TXT={txt}")
        except Exception as e:
            print("[advertiser] send error:", e)

    # send initial unsolicited announcement
    send_response()

    last_reannounce = time.time()

    # listen loop: respond to queries and reannounce periodically
    try:
        while True:
            # periodic reannounce
            if time.time() - last_reannounce > REANNOUNCE_INTERVAL:
                send_response()
                last_reannounce = time.time()
            # non-blocking receive
            sock.settimeout(0.5)
            try:
                data, addr = sock.recvfrom(9000)
            except socket.timeout:
                continue
            except Exception as e:
                print("[advertiser] recv error:", e)
                continue

            # quick parse: check QDCOUNT > 0 and whether query asks for our service
            if len(data) < 12:
                continue
            id, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", data[:12])
            is_query = (flags & 0x8000) == 0
            if not is_query or qdcount == 0:
                # ignore non-queries
                continue

            # parse questions: if any question name == SERVICE_TYPE and type==PTR -> respond
            off = 12
            asked_for_us = False
            try:
                for _ in range(qdcount):
                    # parse name
                    # simple parser (no pointers expected in questions)
                    name_parts = []
                    while True:
                        l = data[off]
                        off += 1
                        if l == 0:
                            break
                        name_parts.append(data[off:off+l].decode())
                        off += l
                    qname = ".".join(name_parts) + "."
                    qtype, qclass = struct.unpack("!HH", data[off:off+4])
                    off += 4
                    # normalize
                    if qname.lower() == SERVICE_TYPE.lower():
                        if qtype in (12, 255):  # PTR or ANY
                            asked_for_us = True
                if asked_for_us:
                    print(f"[advertiser] received query from {addr} asking for {SERVICE_TYPE} -> responding")
                    send_response()
            except Exception as e:
                print("[advertiser] error parsing question:", e)
                # continue
    except KeyboardInterrupt:
        print("advertiser exiting")
    finally:
        sock.close()

if __name__ == "__main__":
    advertiser()
