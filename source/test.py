import shelly

for name in shelly.Devices():
    print(f"{name}\n{'-'*len(name)}\n")
    dev = shelly.Shelly(name)
    for component,data in dev.components.items():
        print(f"  {component}: {data}")
    print("")
