import random
import socket,struct
import threading
import time
import send_recv
import pachet
import psutil

SERVICE_NAME = "Monitor"
HOSTNAME = "ourmonitor.local"
SERVICE_PORT = 6969
TTL = 300
MCAST_GRP = "224.0.0.251"
MCAST_PORT = 5353
SERVICE_TYPE = "_monitor._udp.local."
#INSTANCE_SUFFIX = "._monitor._udp.local."
KILL=0
KILL_ALL=0
txt={}
readMe=0
threads=[]


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

def init(hn,sn,st,res,ttl_ext):
    #print(res)

    global  HOSTNAME,TTL,SERVICE_TYPE
    TTL=int(ttl_ext)
    HOSTNAME = hn
    instance_name = sn+"."+st
    SERVICE_TYPE=st

    ip = get_local_ip()
    print(f"[server] se porneste instanta {instance_name}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack('b', 1))

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)

    mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    try:
        sock.bind(('', MCAST_PORT))
    except Exception as e:
        print("[server] bind error:", e)
        sock.close()
        return

    #def send_response():
     #   sock.sendto(b'Salut de la server we baiet!', (MCAST_GRP, MCAST_PORT))
      #  print(f"[server] sent announcement")
    #send_response()
    global txt
    global KILL,KILL_ALL
    KILL_ALL=0
    def fun_mon():
        #cpu_flag=resurs["CPU"]
        #mem_flag=resurs["RAM"]
        global readMe,txt
        while True:
            if KILL_ALL:
             #   print("STOOOP")
                break
            if res["CPU"]:
                cpu_per = psutil.cpu_percent(1)
                txt["cpu"] = f"{cpu_per}%"
            if res["CPU FREQ"]:
                cpu_freq=psutil.cpu_freq()
                cpu_freq=cpu_freq.current
                txt["cpu freq"]= f"{cpu_freq}MHz"
            if res["RAM"]:
                mem_per = psutil.virtual_memory()[2]
                txt["ram"] = f"{mem_per}%"
            readMe=1
            time.sleep(5)

    threading.Thread(target=fun_mon, daemon=True).start()

    threading.Thread(target=send_recv.recv_q,args=(sock, SERVICE_TYPE), daemon=True).start()


    sock.settimeout(0.5)
    while True:
        if KILL:
            print(f"[server] se opreste instanta {instance_name}")
            KILL_ALL=1
            txt = {}
            KILL=0
            readMe=0
            break
    #   send_response()
        try:
            if send_recv.getMY_Q():
            #mesaj, addr = sock.recvfrom(9000)
            #if addr[0] != ip:
            #if "server" in mesaj.decode():
                    #time.sleep(2)
                    #continue
                print('Am receptionat MYquery trimit raspuns')
                response=pachet.build_response(instance_name,SERVICE_TYPE,HOSTNAME,ip,SERVICE_PORT,txt,TTL)
                send_recv.send_msg(sock,response,"response")
                send_recv.resetMY_Q()
        except socket.timeout:
            continue


   # message, peer_addr = s_peer.recvfrom(512)

