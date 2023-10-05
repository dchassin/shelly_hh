import shelly

devices = "u711.csv"

for name in shelly.Devices(devices):
    print(f"{name}\n{'-'*len(name)}\n")
    dev = shelly.Shelly(name,devices)
    for component,data in dev.components.items():
        print(f"  {component}: {data}")
    print("")
