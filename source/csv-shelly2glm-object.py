import os, csv

def convert(input_file, output_file, options={}):
    """Convert a CSV Shelly device list a GLM model

    Parameters:
        input_file (str) - input file name (csv file)
        ouput_file (str) - output file name (glm file)
        options (dict)
            "hubname" (str) - Name of Home Hub (default is None)
    """

    if "hubname" in options.keys():
        hubname = options["hubname"]
    else:
        hubname = None

    with open(input_file,"r") as csvfile:
        reader = csv.reader(csvfile)
        with open(output_file,"w") as glmfile:
            glmfile.write(f"""
module shelly;
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
}}""")
            if hubname:
                glmfile.write(f"""
object hub {{
    name "{hubname}";""")
            for row in reader:
                glmfile.write(f"""
    object device
    {{
            name "{row[0]}";
            ipaddr "{row[1]}";
    }};
""")
            if hubname:
                glmfile.write(f"""}}""")

if __name__ == "__main__":
    if os.path.exists("shelly_config.csv"):
        convert("shelly_config.csv","shelly_hub.glm",{"hubname":"test_hub"})