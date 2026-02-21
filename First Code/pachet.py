import socket
import struct

import CompressionTest as c
from CompressionTest import decompresie,compresie


TYPE_A = 1
TYPE_PTR = 12
TYPE_TXT = 16
TYPE_SRV = 33
CLASS_IN = 1

def build_header(s="query",an=1):
    id = 0
    flags = 0x0000
    qdcount = 1
    ancount = 0
    nscount = 0
    arcount = 0
    if s == "response":
        id = 0
        flags = 0x8400
        qdcount = 0
        ancount = an
        nscount = 0
        arcount = 0
    return struct.pack("!HHHHHH",id,flags,qdcount,ancount,nscount,arcount)

def build_query(qname:str):
    tip_pachet=struct.pack("!HH",TYPE_PTR,CLASS_IN)
    pachet=build_header()
    d={}
    body,_=compresie(qname,d,"name")
    pachet+=body #am scos 00
    pachet+=tip_pachet
    return pachet

dictionar_pachet={}
nume=b''


def build_rr(name:bytes, rtype: int, rclass: int, ttl: int, rdata: bytes) -> bytes:
    #dictionar_pachet = {}
    #nume=b''
    #name,dictionar_pachet=compresie(rname,dictionar_pachet,"name")

    lenght=len(rdata)

    return name+struct.pack("!HHIH", rtype, rclass, ttl, lenght) + rdata

def build_ptr(instance_name):
    return compresie(instance_name,dictionar_pachet,"name",nume)[0]

def build_a(ip):
    try:
        return socket.inet_aton(ip)
    except Exception:
        return socket.inet_aton("127.0.0.1")

def build_srv(priority: int, weight: int, port: int, name: str) -> bytes:
    return struct.pack("!HHH", priority, weight, port) + compresie(name,dictionar_pachet,"name",nume)[0]

def build_txt(d: dict) -> bytes:
    out = b''
    for k, v in d.items():
        s = f"{k}={v}"
        b = s.encode("utf-8")
        out+= bytes([len(b)])
        out += b
    return out

def build_response(instance,serv,host,ip,port,d,ttl):
    global dictionar_pachet, nume
    h = build_header("response",4)
    body=b''
    dictionar_pachet = {}
    name,dictionar_pachet=compresie(serv,dictionar_pachet,"name")
    nume = name
    body+=build_rr(name,TYPE_PTR,CLASS_IN,ttl,build_ptr(instance))
    nume=b''

    dictionar_pachet = {}
    name, dictionar_pachet = compresie(instance, dictionar_pachet, "name")
    nume = name
    body+=build_rr(name,TYPE_SRV,CLASS_IN,ttl,build_srv(0,0,port,host))
    nume=b''

    dictionar_pachet = {}
    name, dictionar_pachet = compresie(instance, dictionar_pachet, "name")
    body+=build_rr(name,TYPE_TXT,CLASS_IN,ttl,build_txt(d))

    dictionar_pachet = {}
    name, dictionar_pachet = compresie(host, dictionar_pachet, "name")
    body+=build_rr(name,TYPE_A,CLASS_IN,ttl,build_a(ip))
    return h+body

def parse_query(msg,service_t):
    id, flags, qdcount, ancount, nscount, arcount = struct.unpack_from("!HHHHHH", msg, 0)
    if flags != 0x0000 or qdcount == 0:
        return "non_query"
    off=12
    is_for_me=False
    try:
        for i in range(qdcount):
            n, off = decompresie(msg,"name",off)
            qtype, qclass = struct.unpack_from("!HH",msg,off)
            off+=4
            if n.lower()==service_t.lower():
                is_for_me=True
        if is_for_me:
            return "my_query"
        else:
            return "not_mine"
    except Exception as e:
        #print("QUERY_PARSE_ERR: ",e)
        pass

def parse_rr(msg):
    id, flags, qdcount, ancount, nscount, arcount = struct.unpack_from("!HHHHHH", msg, 0)
    off = 12
    raspuns=[]
    rtype, rclass, ttl, rdlength=(0,0,0,0)
    name=''
    for i in range(ancount):
        oinit=off
        try:
            name,off=decompresie(msg,"name",off)
            rtype, rclass, ttl, rdlength = struct.unpack_from("!HHIH", msg, off)
        except Exception as e:
            #print(e)
            break;
        off+=10
        ordata=off-oinit
        rdata = msg[off:off + rdlength]
        off += rdlength
        ans=msg[oinit:off]
        dict = {}
        dict["name"]=name
        dict["type"]=rtype
        dict["class"] = rclass
        dict["ttl"] = ttl
        dict["rdata"] = (ordata,rdata,ans)
        raspuns.append(dict)
    return raspuns

def parse_rdata(dict,cache):
    rtype=dict["type"]
    rname=dict["name"]
    rdata=dict["rdata"][1]
    ans=dict["rdata"][2]
    ordata=dict["rdata"][0]

    if rtype == TYPE_A:
        ip=socket.inet_ntoa(rdata)
        cache.setdefault(rname,{})['a']=ip
        print(f" A: {rname} -> {ip} (ttl={dict['ttl']})")

    elif rtype == TYPE_PTR:
        try:
            name,_=decompresie(ans+b'\x00',"name",ordata)
        except Exception:
            name="<PTR_ERR>"
        print(f" PTR: {rname} -> {name} (ttl={dict['ttl']})")
        cache.setdefault(name,{})['ptr_ttl']=int(dict['ttl'])
    elif rtype == TYPE_SRV:
        priority, weight, port = (0,0,0)
        try:
            priority,weight,port = struct.unpack_from("!HHH",rdata,0)
            hostname,_=decompresie(ans,"name",6+ordata)
        except Exception:
            hostname="<SRV_ERR>"
        srv={"priority":priority,"weight":weight,"port":port,"hostname":hostname}
        print(f" SRV: {rname} -> {srv} (ttl={dict['ttl']})")
        cache.setdefault(rname,{})['srv']=srv
    elif rtype == TYPE_TXT:
        items = []
        i =0
        while i <len(rdata):
            l = rdata[i]
            i+=1
            try:
                items.append(rdata[i:i+l].decode("utf-8"))
            except Exception as e:
                #print(e)
                pass
            i+=l
        d = {}
        for item in items:
            if "=" in item:
                k,v = item.split("=",1)
                d[k]=v
            else:
                d[item]=""
        print(f" TXT: {rname} -> {d} (ttl={dict['ttl']})")
        cache.setdefault(rname,{})['txt']=d





