import sys, os, requests, json

devices = {}

def Devices(file,reload=False):
    global devices
    if not devices or reload:
        with open(file,"r") as fh:
            devices = dict([x.strip().split(",") for x in fh.readlines()])
    return devices

class Shelly:

    timeout = 2

    def __init__(self,name,file):
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


