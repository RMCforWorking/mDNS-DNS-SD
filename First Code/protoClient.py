import socket,struct
import threading
import time

import pachet
import send_recv

MY_IP_ADDR = '192.168.0.101'
MY_PORT = 6000

MCAST_GRP = "224.0.0.251"
MCAST_PORT = 5353
SERVICE_TYPE = "_monitor._udp.local."
TIMEOUT = 70
KILL=0
KILL_ALL=0
cache=[]
sendQext=0

def decrement():
    while True:
        for c in cache:
            for i,v in c.items():
                v['ptr_ttl']-=1
                if v['ptr_ttl']==-1:
                    cache.remove(c)
                break
#        print(cache)
        time.sleep(1)

def init(svT):
    global cache,KILL_ALL,SERVICE_TYPE
    SERVICE_TYPE=svT
    #print(SERVICE_TYPE)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    KILL_ALL=0
    try:
        sock.bind(('', MCAST_PORT))
    except Exception as e:
        print("[client] bind error:", e)
        sock.close()
        return

    mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)


#    s_peer.sendto(b'We  baiet!', (MCAST_GRP, MCAST_PORT))

#    mesaj, addr = s_peer.recvfrom(512)

 #   print('Am receptionat <', mesaj.decode(), '> de la', addr)

    print(f"[client] se porneste acum")

    print(SERVICE_TYPE)
    q=pachet.build_query(SERVICE_TYPE)

   # send_recv.send_msg(sock,q,'query')
    sock.settimeout(0.5)

    threading.Thread(target=decrement, daemon=True).start()
    threading.Thread(target=send_recv.recv_r,args=(sock,SERVICE_TYPE,cache),daemon=True).start()

    timeoutt=2
    global KILL,sendQext
    incr=0
    while True:

        if KILL:
            print(f"[client] se opreste acum")
            KILL_ALL=1
            cache=[]
            KILL=0
            break
        time.sleep(1)
        incr+=1
        if sendQext:

            send_recv.send_msg(sock, q, 'query')
            sendQext=0


        if len(cache) or incr==timeoutt:
            #print(cache)
            timeoutt = 600
            incr=0
        else:
            timeoutt=2
            send_recv.send_msg(sock, q, 'query')

            #while True:
     #   data, addr = sock.recvfrom(512)
      #  if "clientul" in data.decode():
     #       continue
      #  print(f"[clientul] primit: {data.decode()} de la {addr}")
       # sock.sendto(b"Salut, clientul te-a auzit!", (MCAST_GRP,MCAST_PORT))
       # print(f"am trimis la {MCAST_GRP} si {MCAST_PORT}")

if __name__ == "__main__":
    init()