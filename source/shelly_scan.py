"""Scan for Shelly devices on local network

Syntax
------
    python3 shelly_scan.py [-n|--network=IPRANGE[,...]] [-t|--timeout=SECONDS]
        [-m|--maxqueue=INTEGER] [-f|--format=FORMAT] [-r|--rowdelim=STR]
        [-c|--coldelim=STR] [-q|--quote=STR] [-v|--verbose] [-d|--debug]
        [-s|--silent] [-l|--longscan] [-h|--help|help] [-o|--output[=FILENAME]]

This command scans the local network for Shelly devices and generates the
result of the search in various formats.

Options
-------

    `[-c|--coldelim=STR]`: Change the column delimeter for CSV output
            (default `: `)

    `[-d|--debug]`: Enable traceback on errors

    `[-f|--format=FORMAT]`: Change output format. Valid formats are `list`
            (default), `name`, `addr`, `csv`, `table`, and `pandas`.

    `[-h|--help|help]`: Get this help output.

    `[-l|--longscan]`: Enable long scanning (i.e., more than 256 addresses)

    `[-m|--maxqueue=INTEGER]`: Change the size of the asynchronous queue
            (default 1024)

    `[-n|--network=IPRANGE[,...]]`: Specify the network IP ranges to scan
            (default is current network broadcast range).If the broadcast
            range ends in `.255.255` then `--longscan` must be enabled.

    `[-o|--output[=FILENAME]]`: Specify the output file (default stdout)

    `[-q|--quote=STR]`: Change the quote character on output fields
            (default '')

    `[-r|--rowdelim=STR]`: Change the row delimiter string (default newline)

    `[-s|--silent]`: Silence error message output to /dev/stderr

    `[-t|--timeout=SECONDS]`: Change the request timeout (default 2 seconds)

    `[-v|--verbose]`: Enable verbose output

Example
-------

Scan the local network and generate a GLM file to access the devices found:

    gridlabd shelly scan -f=glm

Scan the local network and generate a `shelly.json` configuration file:

    gridlabd shelly scan -f=csv -o=shelly.csv

"""

import sys, os
import asyncio
import aiohttp
import json
import datetime
import socket, netifaces
import re
import pandas

VERBOSE     = False
PROGRESS    = False
QUIET       = False
DEBUG       = True
TIMEOUT     = 2
MAXQUEUE    = 256
NETWORKS    = []
FORMAT      = 'csv'
ROWDELIM    = '\n'
COLDELIM    = ','
QUOTE       = ''
LONGSCAN    = False
OUTPUT      = None

result = {}

E_OK = 0
E_INVAL = 22

class ShellyScanError(Exception):
    pass

def error(msg,code=None,**kwargs):
    if DEBUG:
        raise ShellyScanError(msg)
    elif not QUIET:
        if not "file" in kwargs:
            kwargs["file"] = sys.stderr
        if not "flush" in kwargs:
            kwargs["flush"] = True
        print(f"ERROR [scan]: {msg}",**kwargs)
        if type(code) is int:
            exit(code)
        elif code != None:
            raise Exception(f"invalid code '{code}'")

def verbose(msg,**kwargs):
    if VERBOSE:
        if not "file" in kwargs:
            kwargs["file"] = sys.stderr
        if not "flush" in kwargs:
            kwargs["flush"] = True
        print(f"VERBOSE [scan]: {msg}",**kwargs)

def progress(msg,**kwargs):
    if PROGRESS and not VERBOSE:
        if not "file" in kwargs:
            kwargs["file"] = sys.stderr
        if not "flush" in kwargs:
            kwargs["flush"] = True
        print(msg,**kwargs)

async def task(name, work_queue):

    async with aiohttp.ClientSession(connector = aiohttp.TCPConnector(limit=MAXQUEUE)) as session:
        while not work_queue.empty():
            url = await work_queue.get()
            verbose(f"{name}: GET {url}")
            try:
                async with session.get(url,timeout=TIMEOUT) as response: 
                #,hooks={"response":lambda *x,**y:found(name,*x,**y)}) as response
                    found(name,url,await response.text())
            except Exception as err:
                pass
            #     e_type,e_value,e_trace = sys.exc_info()
            #     print(f"EXCEPTION [{e_type.__name__}]: {url} failed ({e_value})",file=sys.stderr)
            # except TimeoutError:
            #     pass
            # except aiohttp.ClientConnectionError:
            #     pass

def found(name,url,response,**kwargs):
    try:
        data = json.loads(response)
        if data["id"].startswith("shelly"):
            result[name] = config=data
            verbose(f"found {name} at {url} - result = {data}")
        else:
            verbose(f"device at {url} is not a Shelly - response = {data}")
    except:
        verbose(f"device at {url} is not a Shelly - response = {response}")

async def scanner():
    work_queue = asyncio.Queue()
    iplist = []
    tasks = []
    for iprange in NETWORKS:
        start,stop = [[int(y) for y in x.split(".")] for x in iprange.split("-")]
        for d in range(start[0],stop[0]+1):
            for c in range(start[1],stop[1]+1):
                for b in range(start[2],stop[2]+1):
                    for a in range(start[3],stop[3]+1):
                        ipaddr = f"{d}.{c}.{b}.{a}"
                        iplist.append(ipaddr)
    treq = datetime.timedelta(seconds=(len(iplist)/MAXQUEUE)*(TIMEOUT))
    progress(f"Scanning {len(iplist)} addresses in groups of {MAXQUEUE} devices will take about {treq}",end="")

    for n in range(0,len(iplist),MAXQUEUE):
        progress(".",end="")
        for ipaddr in iplist[n:n+MAXQUEUE]:
            verbose(f"QUEUE: {ipaddr}")
            await work_queue.put(f"http://{ipaddr}/shelly")
        for ipaddr in iplist:
            tasks.append(asyncio.create_task(task(ipaddr,work_queue)))
        await asyncio.gather(*tasks)

def _bool(value):
    if type(value) is str:
        if value.lower() in ["true","yes","y","t"]:
            return True
        elif value.lower() in ["false","no","n","f"]:
            return False
    try:
        return value if type(value) is bool else bool(int(value))
    except:
        raise Exception(f"'{value}' is not a boolean")

def scan(format='list'):
    """Scan for Shelly devices

    Arguments
    ---------
        format (str) - specify format of return value

    Returns
    -------
        (list) - if `format` is 'list' (default)

        (dict) - if `format` is 'name' or 'addr', which selects key vlaue
        
        (str) - if format is 'csv' or 'table', which determines whether header
                row is included
        
        (pandas.DataFrame) - if format is 'pandas'

    Exceptions
    ----------
        Various - Exceptions from pandas, netifaces, requests, etc.
    """
    if not format in ["list","name","addr","csv","table","pandas","glm"]:
        raise Exception(f"'{format}' is not a valid format")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8',80)) # use google to create a working socket without sending anything
        ipaddr = s.getsockname()[0]
    except:
        error("unable to get host ipaddr",E_INVAL)
    try:
        global NETWORKS
        if not NETWORKS:
            iflist = netifaces.interfaces()
            for iface in iflist:
                spec = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in spec:
                    for addrs in spec[netifaces.AF_INET]:
                        if addrs['addr'] == ipaddr:
                            ipmask = addrs['netmask']
                            ipcast = addrs['broadcast']
                            if ipcast.endswith(".255.255") and not LONGSCAN:
                                raise Exception("long scan is not enabled")
                            verbose(f"host ipaddr = {ipaddr}, netmask = {ipmask}, broadcast = {ipcast}",file=sys.stderr,flush=True)
                            NETWORKS = [ipcast.replace("255","0") + "-" + ipcast]
        asyncio.run(scanner())
    except:
        error("unable to get host interfaces")

    rows = []
    for addr,data in result.items():
        rows.append([data['name'],addr])#f"{re.sub('[^a-z]','_',data['name'].lower())},{addr}")
    if format == 'list':
        return rows
    elif format == 'name':
        return dict(rows)
    elif format == 'addr':
        return dict([(y,x) for x,y in rows])
    elif format == 'csv':
        return ROWDELIM.join([COLDELIM.join([QUOTE+y+QUOTE for y in x]) for x in rows])
    elif format == 'table':
        return f"{QUOTE}name{QUOTE}{COLDELIM}{QUOTE}addr{QUOTE}{ROWDELIM}"+ROWDELIM.join([COLDELIM.join([QUOTE+y+QUOTE for y in x]) for x in rows])
    elif format == 'pandas':
        return pandas.DataFrame(rows,columns=["name","addr"])
    elif format == 'glm':
        return as_glm(rows)

def as_glm(rows):
    # header = f"""// generated by '{' '.join(sys.argv)}' at {datetime.datetime.now()}
    header = f"""module shelly;
class hub
{{
    on_init "python:shelly.hub_init";
    on_sync "python:shelly.hub_sync";
}}
class device
{{
    char32 ipaddr;
    enumeration {{OFFLINE=0, ONLINE=1}} status;
    enumeration {{OFF=0, ON=1}} switch;
    bool output;
    double power[W];
    double voltage[V];
    double current[A];
    double energy[Wh];
    timestamp last_update;
    on_init "python:shelly.device_init";
    on_precommit "python:shelly.device_read";
    on_commit "python:shelly.device_write";
}}
object hub {{
"""
    footer = "}"
    return header + "\n".join([f"""    object device
    {{
        name "{name}";
        ipaddr "{addr}";
    }};
"""+footer for name,addr in rows])

if __name__ == "__main__":

    try:
        for arg in sys.argv[1:]:
            spec = arg.split("=")
            if len(spec) == 1:
                tag = spec[0]
                value = True
            else:
                tag = spec[0]
                value = "=".join(spec[1:])
            if tag in ["-c","--coldelim"]:
                COLDELIM = value 
            elif tag in ["-d","--debug"]:
                DEBUG = _bool(value)
            elif tag in ["-f","--format"]:
                FORMAT = value
            elif tag in ["-h","--help","help"]:
                print(__doc__,file=sys.stdout)
                exit(E_OK)
            elif tag in ["-l","--longscan"]:
                LONGSCAN = value
            elif tag in ["-m","--maxqueue"]:
                MAXQUEUE = int(value)
            elif tag in ["-n","--network"]:
                NETWORKS = value.split(",")
            elif tag in ["-o","--output"]:
                OUTPUT = "/dev/stdout" if value == True else value
            elif tag in ["-q","--quote"]:
                QUOTE = value
            elif tag in ["-r","--rowdelim"]:
                ROWDELIM = value
            elif tag in ["-t","--timeout"]:
                TIMEOUT = int(value)
            elif tag in ["-s","--silent"]:
                QUIET = _bool(value)
            elif tag in ["-v","--verbose"]:
                VERBOSE = _bool(value)
            else:
                raise Exception(f"option '{arg}' is invalid")
    except Exception as err:
        error(err,E_INVAL)

    with open(OUTPUT,"w") if type(OUTPUT) is str else sys.stdout as fh:
        print(scan(format=FORMAT),file=fh)

