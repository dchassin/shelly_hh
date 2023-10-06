import sys, os
import json
import datetime
import requests

device_addr = {}
device_file = None
device_data = {}
VERBOSE = True
DEBUG = False

def verbose(msg):
    if VERBOSE:
        print(f"VERBOSE [shelly]: {msg}",file=sys.stderr)

def Devices(file,reload=False):
    global device_addr
    global device_file
    if not device_file or file != device_file or reload:
        with open(file,"r") as fh:
            device_addr = dict([x.strip().split(",") for x in fh.readlines()])
            device_file = file
    return device_addr

class Shelly:

    timeout = 2

    def __init__(self,name,file=None):
        if not file:
            file = device_file
        self.ipaddr = Devices(file)[name]
        self.config = self._get()
        self.components = self.GetStatus("shelly")

    def _get(self,query=None,**kwargs):
        try:
            if query:
                reply = requests.post(f"http://{self.ipaddr}/rpc/{query}",timeout=self.timeout,json=kwargs)
            else:
                reply = requests.get(f"http://{self.ipaddr}/shelly",timeout=self.timeout)

            if reply.status_code == 200:
                if not query:
                    self.config = reply
                return json.loads(reply.text.encode())
            else:
                return dict(error=reply.status_code,message=reply.text.encode())
        except Exception as err:
            return dict(error="exception",message=str(err))

    def GetConfig(self,component,**data):
        return self._get(f"{component.title()}.GetConfig",**data)

    def GetStatus(self,component,**data):
        return self._get(f"{component.title()}.GetStatus",**data)

def load(obj,ts):
    verbose(f"load(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    Devices(obj+".csv")
    verbose(f"Devices: {device_addr}")
    device_data[obj] = {}
    return 0

def save(obj,response, **kwargs):
    verbose(f"save(obj='{obj}',response={response},kwargs={kwargs})")
    if response.status_code == 200:
        verbose(f"  code 200: {response.text}")
        device_data[obj] = json.loads(response.text)
        verbose(f"device_data['{obj}'] = {device_data[obj]}")

def init(obj,ts):
    verbose(f"init(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    return 0

def sync(obj,ts):
    verbose(f"sync(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    return ts+1

def read(obj,ts):
    verbose(f"read(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    try:
        requests.get(f"http://{device_addr[obj]}/rpc/Switch.GetStatus?id=0",timeout=1,hooks={"response":lambda x,**y:save(obj,x,**y)})
    except Exception as err:
        # print(f"Exception('{err}')",file=sys.stderr)
        gridlabd.warning(f"read(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}'): request timeout")
    return gridlabd.NEVER

def write(obj,ts):
    verbose(f"write(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    return ts+1

if __name__ == "__main__":
    Devices("b27.csv")
    print(device_addr)
    for dev in device_addr:
        print(Shelly(dev).GetStatus("switch",id=0))