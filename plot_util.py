import pandas
import os
import subprocess

# General configuration.
COLORS = [
    "rgb(255,255,106)",
    "rgb(31,120,180)",
    "rgb(178,223,138)",
    "rgb(51,160,44)",
    "rgb(251,154,153)",
    "rgb(207,233,252)",
    "rgb(188, 189, 34)",
    "rgb(23, 190, 207)",
    "rgb(240, 74, 62)",
    "rgb(23, 190, 207)",
]

plotconfig = {
    "rwlock": {
        "label": "EBR-RQ",
        "color": COLORS[7],
        "symbol": 1,
        "macrobench": "RQ_RWLOCK",
    },
    "lockfree": {
        "label": "EBR-RQ-LF",
        "color": COLORS[1],
        "symbol": 0,
        "macrobench": "RQ_LOCKFREE",
    },
    "rlu": {"label": "RLU", "color": COLORS[4], "symbol": 3, "macrobench": "RQ_RLU"},
    "bundle": {
        "label": "Bundle",
        "color": COLORS[3],
        "symbol": 2,
        "macrobench": "RQ_BUNDLE",
    },
    "rbundle": {
        "label": "Bundle-restart",
        "color": COLORS[0],
        "symbol": 5,
        "macrobench": "",
    },
    "unsafe": {
        "label": "Unsafe",
        "color": COLORS[5],
        "symbol": 4,
        "macrobench": "RQ_UNSAFE",
    },
    "vcas": {"label": "vCAS", "color": COLORS[6], "symbol": 6, "macrobench": None},
    "tsbundle": {
        "label": "Bundle-rqts",
        "color": COLORS[8],
        "symbol": 7,
        "macrobench": "",
    },
}


def update_opacity(colorstr, opacity):
    temp = colorstr.split("(")
    return "rgba(" + temp[1][:-1] + ", " + str(opacity) + ")"


relaxconfig = {
    "relax1": {"label": "T=1", "color": COLORS[0], "symbol": 1},
    "relax2": {"label": "T=2", "color": COLORS[1], "symbol": 0},
    "relax5": {"label": "T=5", "color": COLORS[2], "symbol": 3},
    # 'relax10': {'color': 'seagreen', 'symbol': 2},
    # 'relax20': {'color': 'darkorange', 'symbol': 5},
    "relax50": {"label": "T=50", "color": COLORS[3], "symbol": 4},
    "relax100": {"label": "T=100", "color": COLORS[4], "symbol": 6},
    "relax1k": {"label": "T=1000", "color": COLORS[5], "symbol": 7},
    # 'relax10k': {'label': 'T=10000', 'color': COLORS[6], 'symbol': 8},
    "ubundle": {"label": "T=infinity", "color": COLORS[9], "symbol": 9},
}

delayconfig = {
    "delay0": {"label": "d=0ms", "color": COLORS[0], "symbol": 1},
    "delay1000": {"label": "d=1ms", "color": COLORS[1], "symbol": 0},
    "delay5000": {"label": "T=5ms", "color": COLORS[2], "symbol": 3},
    "delay10000": {"label": "T=10ms", "color": COLORS[3], "symbol": 4},
    "delay100000": {"label": "T=100ms", "color": COLORS[4], "symbol": 6},
    "nofree": {"label": "Leaky", "color": COLORS[5], "symbol": 7},
}

separate_unsafe = True

# Global variables used for formatting.
axis_font_ = {}
legend_font_ = {}
x_axis_layout_ = {}
y_axis_layout_ = {}
layout_ = {}


def reset_base_config():
    # Clear out any existing values.
    axis_font_.clear()
    legend_font_.clear()
    x_axis_layout_.clear()
    y_axis_layout_.clear()
    layout_.clear()

    # The following should be called before every plot to ensure that there are no changes visible from previous method calls.
    axis_font_["family"] = "Times-Roman"
    axis_font_["size"] = 72
    axis_font_["color"] = "black"

    legend_font_["family"] = "Times-Roman"
    legend_font_["size"] = 24
    legend_font_["color"] = "black"

    x_axis_layout_["type"] = "category"
    x_axis_layout_["title"] = {"text": ""}
    x_axis_layout_["title"]["font"] = axis_font_.copy()
    x_axis_layout_["tickfont"] = axis_font_.copy()
    x_axis_layout_["zerolinecolor"] = "black"
    x_axis_layout_["gridcolor"] = "black"
    x_axis_layout_["gridwidth"] = 2
    x_axis_layout_["linecolor"] = "black"
    x_axis_layout_["linewidth"] = 4
    x_axis_layout_["mirror"] = True

    y_axis_layout_["title"] = {"text": ""}
    y_axis_layout_["title"]["font"] = axis_font_.copy()
    y_axis_layout_["tickfont"] = axis_font_.copy()
    y_axis_layout_["zerolinecolor"] = "black"
    y_axis_layout_["gridcolor"] = "black"
    y_axis_layout_["gridwidth"] = 2
    y_axis_layout_["linecolor"] = "black"
    y_axis_layout_["linewidth"] = 4
    y_axis_layout_["mirror"] = True

    layout_["xaxis"] = x_axis_layout_
    layout_["yaxis"] = y_axis_layout_
    layout_["plot_bgcolor"] = "white"
    layout_["margin"] = dict(l=0, r=10, t=10, b=0)


def parse_config(filepath):
    required_configs = {"maxthreads": int, "threadincrement": int}
    config = {}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            entry = line.split("=", maxsplit=1)
            if entry[0] not in required_configs.keys():
                print("Ignoring line in config.mk: {}".format(line))
                continue
            config[entry[0]] = required_configs[entry[0]](entry[1])
    return config


def parse_experiment_list_generate(filepath, experiment_commands):
    experiments = []
    configs = {"datastructures": None, "ksizes": None}
    done = {"datastructures": False, "ksizes": False}
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            
            # Check whether this line indicates an experiment to run skip parsing the configuration if so
            if len(experiment_commands) > 0:
                detected = False
                for e in experiment_commands:
                    if e in line and "#<" in line:
                        experiments.append(e)
                        detected = True
                        break
                if detected:
                    continue

            for k in configs.keys():
                if k in line and "=" in line:
                    entry = line.split("=", maxsplit=1)
                    filtered = "".join((filter(lambda x: x not in ['"'], entry[1])))
                    value = filtered.split(" ")  # list is space separated
                    if k == "ksizes":
                        configs[entry[0]] = [int(v) for v in value]
                    else:
                        configs[entry[0]] = value
                    done[entry[0]] = True
    return experiments, configs


def parse_runscript(filepath, config_list):
    configs = {}
    done = {}
    for c in config_list:
        configs[c] = None
        done[c] = False
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            for k in configs.keys():
                if k in line:
                    entry = line.split("=", maxsplit=1)
                    filtered = "".join((filter(lambda x: x not in ['"'], entry[1])))
                    if k == "trials":
                        configs[k] = int(filtered)
                    done[k] = True
            if False in done.values():
                continue
            else:
                break
    return configs



class CSVFile:
    """A wrapper class to read and manipulate data from output produced by make_csv.sh"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.df = pandas.read_csv(filepath, sep=",", engine="c", index_col=False)

    def __str__(self):
        return str(self.df.columns)

    def getdata(self, filter_col, filter_with):
        data = self.df.copy()  # Make a copy of the data frame to return.
        for o, w in zip(filter_col, filter_with):
            # Filter the data for the rows matching the column.
            data = data[data[o] == w]
        # x = sorted(data[x_axis].unique())  # Get the unique x axis values
        # y = data[y_axis].to_numpy()  # Get corresponding y values
        # return {"x": x, "y": y}
        return data

    # Tries to create a csv file for the given data structure (ds) and number of trials (n).
    @staticmethod
    def get_or_gen_csv(dirpath, ds, n):
        filepath = os.path.join(dirpath, ds + ".csv")
        assert os.path.exists(os.path.join("./microbench", "make_csv.sh"))
        if not os.path.exists(filepath):
            print("No .csv file found for " + ds + ". Generating it now...")
            subprocess.call(
                "./microbench/make_csv.sh " + dirpath + " " + str(n) + " " + ds,
                shell=True,
            )
        return filepath
