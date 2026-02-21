import os
import threading
import time
import tkinter as tk

import protoServer


class SRVGUI:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    A = None
    B = None
    hostn=""
    srvN=""
    srvT=""
    chkStart=0
    res= {"CPU": 0,"RAM":0,"CPU FREQ":0}
    ttl=""

    def __init__(self, gui):
        self.gui = gui
        self.gui.title('Server')

        self.gui.geometry("900x300")
        self.cpu=tk.IntVar()
        self.ram=tk.IntVar()
        self.freq=tk.IntVar()

        self.ttl_lbl=tk.Label(master=self.gui,
                                   text="TTL value:")

        self.hnname_lbl = tk.Label(master=self.gui,
                                   text="Server Hostname:")

        self.svname_lbl=tk.Label(master=self.gui,
                                 text="Service name: ")

        self.svtype_lbl = tk.Label(master=self.gui,
                                  text="Service Type: ")
        self.mon_res_lbl = tk.Label(master=self.gui,
                                   text="Resouces: ")

        self.startstop_btn = tk.Button(master=self.gui,
                                      text="start/stop server",
                                      command=self.startStop,height=3,width=15)

        self.ttl_str=tk.Text(self.gui, width=10, height=1)
        self.hn_str = tk.Text(self.gui, width=25, height=1)
        self.svn_str = tk.Text(self.gui, width=25, height=1)
        self.svt_str = tk.Text(self.gui, width=25, height=1)

        self.textBox=tk.Text(self.gui,width=50, height=8)
        self.cpubox = tk.Checkbutton(self.gui,text="CPU usage",onvalue=1,offvalue=0,variable=self.cpu)
        self.rambox = tk.Checkbutton(self.gui, text="RAM usage", onvalue=1, offvalue=0, variable=self.ram)
        self.freqbox = tk.Checkbutton(self.gui, text="CPU freq", onvalue=1, offvalue=0, variable=self.freq)

        # alignment on the grid
        self.hnname_lbl.grid(row=0, column=0)
        self.svname_lbl.grid(row=1, column=0)
        self.svtype_lbl.grid(row=2, column=0)
        self.hn_str.grid(row=0, column=1)
        self.svn_str.grid(row=1, column=1)
        self.svt_str.grid(row=2, column=1)
        self.textBox.grid(row=6,column=2)
        self.startstop_btn.grid(row=1, column=2)
        self.mon_res_lbl.grid(row=4,column=0)
        self.cpubox.grid(row=4,column=1)
        self.freqbox.grid(row=4,column=2)
        self.rambox.grid(row=4,column=3)
        self.ttl_lbl.grid(row=6,column=0)
        self.ttl_str.grid(row=6,column=1)

        self.gui.mainloop()


    def receiveData(self):
        self.hostn = self.hn_str.get("1.0", tk.END)
        self.hostn=self.hostn.splitlines()[0]
        self.srvN = self.svn_str.get("1.0",tk.END)
        self.srvN = self.srvN.splitlines()[0]
        self.srvT = self.svt_str.get("1.0",tk.END)
        self.srvT = self.srvT.splitlines()[0]
        self.res["CPU"]=self.cpu.get()
        self.res["RAM"]=self.ram.get()
        self.res["CPU FREQ"]=self.freq.get()
        self.ttl=self.ttl_str.get("1.0",tk.END)
        self.ttl = self.ttl.splitlines()[0]

    def startStop(self):
        if self.chkStart==0:
            self.chkStart=1
        else:
            self.chkStart=0
        if self.chkStart:
            self.receiveData()
            #print(len(self.hostn))
            #protoServer.KILL=0
            if len(self.hostn) and len(self.srvN) and len(self.srvT) and len(self.res) and len(self.ttl):
                threading.Thread(target=protoServer.init, args=(self.hostn, self.srvN, self.srvT, self.res,self.ttl),
                                         daemon=True).start()
                threading.Thread(target=self.writeOn, daemon=True).start()
            else:
                self.chkStart=0
        else:
            protoServer.KILL=1


    def writeOn(self):
        while True:
            if protoServer.readMe:
                dict = protoServer.txt
                self.textBox.insert(tk.END,str(dict)+"\n")
                #print(dict)
                protoServer.readMe=0
                time.sleep(3)
            if not self.chkStart:
                try:
                    self.textBox.delete("1.0", tk.END)
                except Exception:
                    pass
                break

if __name__ == '__main__':
    root = tk.Tk()
    root.title('server GUI')
    app = SRVGUI(root)
    root.mainloop()
