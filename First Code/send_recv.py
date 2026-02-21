import socket
import pachet

MCAST_GRP = "224.0.0.251"
MCAST_PORT = 5353

MY_Q=False

def getMY_Q():
    global MY_Q
    return MY_Q
def resetMY_Q():
    global MY_Q
    MY_Q= False

def send_msg(sock:socket,msg,flag):
    if flag == "response":
        try:
            sock.sendto(msg,(MCAST_GRP,MCAST_PORT))
            print(f"[server] sent response")
        except Exception as e:
            print("ERR_SERVER",e)
    elif flag == "query":
        try:
            sock.sendto(msg,(MCAST_GRP,MCAST_PORT))
            print(f"[client] sent a query")
        except Exception as e:
            print("ERR_CLIENT")

def recv_q(sock:socket,service_type):
    global MY_Q
    sock.settimeout(0.5)
    while True:
        msg=b''
        try:
            msg,addr = sock.recvfrom(9000)
        except socket.timeout:
            continue
        except Exception as e:
            #print("[server] recv err: ",e)
            continue
        if len(msg) < 12:
            continue #mesajul este mai scurt decat header
        ret = pachet.parse_query(msg,service_type)
        if ret=="my_query":
            MY_Q=True
        else:
            continue



def recv_r(sock:socket,serv,cacheL):
    sock.settimeout(0.5)
    while True:
        msg=b''
        addr=0
        try:
            msg,addr = sock.recvfrom(9000)
        except socket.timeout:
            continue
        except Exception as e:
            #print("[client] recv err: ",e)
            continue

        if len(msg)<12:
            continue
        raspunsuri=pachet.parse_rr(msg)
        cache={}
        cauta = 0
        g=0
        for r in raspunsuri:
            if r['name']==serv or cauta==1:
                pachet.parse_rdata(r,cache)
                cauta=1
        if len(raspunsuri) and cauta:
            print(f"\n[client] a primit pachet de la {addr} len={len(msg)}")
            k2 = list(cache.keys())[0]
            for c in cacheL:
                k = list(c.keys())[0]
                if k == k2:
                    cacheL[cacheL.index(c)]=cache
                    g=1
                    break
            if not g:
                cacheL.append(cache)

            print(cacheL)





