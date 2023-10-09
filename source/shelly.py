"""Shelly device accessor library
"""
import sys, os
import json
import datetime
import requests

VERBOSE = True
DEBUG = False
UPDATE_RATE = 1 # second

def verbose(msg):
    if VERBOSE:
        print(f"VERBOSE [shelly]: {msg}",file=sys.stderr)

device_file = "shelly_config.csv" if os.path.exists("shelly_config.csv") else None
device_addr = {}
device_data = {}

def Devices(file=device_file,reload=False):
    """Load device list from file"""
    global device_addr
    global device_file
    if not device_data or file != device_file or reload:
        if file:
            with open(file,"r") as fh:
                device_addr = dict([x.strip().split(",") for x in fh.readlines()])
                device_file = file
    return device_addr

Devices()

class Shelly:
    """Shelly accessor"""
    timeout = 2

    def __init__(self,name,file=None):
        """Shelly accessor constructor"""
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

def hub_init(obj,ts):
    """Hub initialization event handler

    Loads device list hub:name.csv and initializes device data dictionary
    """
    verbose(f"hub_init(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    if os.path.exists(obj+".csv"):
        Devices(obj+".csv")
    verbose(f"Devices: {device_addr}")
    device_data[obj] = {}
    return 0

def hub_sync(obj,ts):
    """Hub synchronization event handler

    Sets the update rate of the home hub, e.g., 1 second
    """
    verbose(f"hub_sync(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    return ts + UPDATE_RATE

def device_sync(obj,response, **kwargs):
    """Synchronize local data with remote device data"""
    verbose(f"device_sync(obj='{obj}',response={response},kwargs={kwargs})")
    if response.status_code == 200:
        verbose(f"  code 200: {response.text}")
        device_data[obj] = json.loads(response.text)
        verbose(f"  device_data['{obj}'] = {device_data[obj]}")

def device_init(obj,ts):
    """Initialize local device data"""
    verbose(f"device_init(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    return 0

def device_read(obj,ts):
    """Read remote device into local data"""
    verbose(f"device_read(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    try:
        requests.get(f"http://{device_addr[obj]}/rpc/Switch.GetStatus?id=0",timeout=1,hooks={"response":lambda x,**y:device_sync(obj,x,**y)})
    except Exception as err:
        # print(f"Exception('{err}')",file=sys.stderr)
        gridlabd.warning(f"read(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}'): request timeout")
    return gridlabd.NEVER

def device_write(obj,ts):
    """Write local data to remote device"""
    verbose(f"device_write(obj='{obj}',ts='{datetime.datetime.fromtimestamp(ts)}')")
    return ts+1

