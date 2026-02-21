import struct


def compresie(s:str,dict,flag="",dl=b''):
    if s == "":
        return b"\x00"
    if flag== "name":
        if s.endswith("."):
            s = s[:-1]
        words=s.split(".")
    else:
        words=s.split()
    masca=49152
    c=b''
    for word in words:
        if word not in dict:
            dict[word]=(len(c)+len(dl))
            c=c+bytes([len(word)])+word.encode()
        else:
            x=masca|dict[word]
           # c+=b'\\'
            c+=x.to_bytes(2,"big")
            #c+=b'\x00'
    c+=b'\x00'
    return c,dict

def get(sir:bytes,k):
    #print(k)
    ln=int(sir[k])
    word = sir[k+1:k+ln+1].decode()
    return word

def decompresie(s,flag="",o=0):
    sep=" "
    if flag == "name":
        sep="."
    max=len(s)
    masca = 192
    words=""
    k=o
    while k<max:
        ln=int(s[k])
        if ln == 0:
            k+=1
            break
        if ln < 192:
            #print(ln)
            word=s[k+1:k+ln+1].decode()
            k = k + ln + 1
        else:
            k+=1
            ln=ln & (~masca)
            ln*=8
            ln+=int(s[k])
            #ln = ln & (~masca)
            word = get(s,ln)
            k+=1
        words += word
        words += sep
    return words, k


if __name__ == '__main__':
    s="Ne place sa lucram la retele de calculatoare doar ca ne este greu sa intelegem retelele de calculatoare fara sa lucram"
    s3="cpuMon.monitor.udp.local."
    s4="ramMon.monitor.udp.local."
    d={}
    cu=compresie(s3,d,"name")[0]
    cu2=cu+compresie(s4,d,"name",cu)[0]
    #cu2+=b'\x00'+compresie(s3,d,"name")[0]
    #cu2 += b'\x00' + compresie(s4, d, "name")[0]
    print(cu2)
    #print()
 #   print(cu[13])
  #  print(get(cu,13))
    s2,of=decompresie(cu2,"name")
    print(s2)
    s2,of=decompresie(cu2,"name",of)
    print(s2)
    #s2, of = decompresie(cu2, "name", of)
    #print(s2)
    #s2, of = decompresie(cu2, "name", of)
    #print(s2)
