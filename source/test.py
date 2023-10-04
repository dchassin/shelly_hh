import sys, os, requests, json

class Shelly:

    def __init__(self,ipaddr):
        self.ipaddr = ipaddr
        self.config = self._get()
        self.components = self.GetStatus("shelly")

    def _get(self,query=None,**kwargs):
        if query:
            reply = requests.post(f"http://{self.ipaddr}/rpc/{query}",json=kwargs)
        else:
            reply = requests.get(f"http://{self.ipaddr}/shelly")
        if reply.status_code == 200:
            if not query:
                self.config = reply
            return json.loads(reply.text.encode())
        else:
            return dict(error=reply.status_code,message=reply.text.encode())

    def GetConfig(self,component,**data):
        return self._get(f"{component.title()}.GetConfig",**data)

    def GetStatus(self,component,**data):
        return self._get(f"{component.title()}.GetStatus",**data)

# dev = Shelly("10.0.0.89")
# print(dev.config)
# print(dev.components)
# for component in dev.components:
#     print(dev.GetConfig(component))
#     print(dev.GetStatus(component))

