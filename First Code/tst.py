# sample python program for gethostname
import random
import socket
import pachet
import psutil

SERVICE_NAME = "RamMon"
HOSTNAME = "rammon.local"
SERVICE_PORT = 8080
TTL = 200
MCAST_GRP = "224.0.0.251"
MCAST_PORT = 5353
SERVICE_TYPE = "_monitor._udp.local."
INSTANCE_SUFFIX = "._monitor._udp.local."
REANNOUNCE_INTERVAL = max(1, TTL // 3)

if __name__ == '__main__':
    instance=f"{SERVICE_NAME}{INSTANCE_SUFFIX}"
    txt={}
    txt["ram"] = f"{round(random.random() * 100.0, 2)}%"
    txt["ram2"]=f"{round(random.random() * 100.0, 2)}%"
    msg=pachet.build_response(instance,SERVICE_TYPE,HOSTNAME,"192.168.50.4",SERVICE_PORT,txt,TTL)
    #msg = pachet.build_query(SERVICE_TYPE)
    cache={}
    if len(msg) < 12:
        print("err msg")
    ret = pachet.parse_query(msg, SERVICE_TYPE)
    if ret == "my_query":
        print("succes")
    else:
        print(ret)

    raspunsuri = pachet.parse_rr(msg)

    for r in raspunsuri:
        pachet.parse_rdata(r, cache)

    txt["ram"] = f"{round(random.random() * 100.0, 2)}%"
    txt["ram2"] = f"{round(random.random() * 100.0, 2)}%"
    msg=pachet.build_response(instance,SERVICE_TYPE,HOSTNAME,"192.168.50.5",SERVICE_PORT,txt,TTL)
    if len(msg) < 12:
        print("err msg")
    ret = pachet.parse_query(msg, SERVICE_TYPE)
    if ret == "my_query":
        print("succes")
    else:
        print(ret)

    raspunsuri = pachet.parse_rr(msg)

    for r in raspunsuri:
        pachet.parse_rdata(r, cache)

    print("\n")
    for k,v in cache.items():
        print(k, ":", v)

    cpu_per = psutil.cpu_percent(1)

    mem_per = psutil.virtual_memory()[2]
    print(cpu_per,mem_per)
