import numpy as np
import plotly
import plotly.graph_objects as go
from plotly import subplots
from plot_util import *

import argparse
from plotly.subplots import make_subplots
import math
from absl import app
from absl import flags

FLAGS = flags.FLAGS

# Whether or not to plot the microbenchmark and where to find the data.
flags.DEFINE_bool("microbench", False, "Plot microbenchmark results")
flags.DEFINE_string(
    "microbench_dir",
    "./microbench/data",
    "Location of microbenchmark data. If the folder corresponding to each experiment does not contain a .csv file, it will be automatically generated",
)

# Whether or not to plot the macrobenchmark and where to find the data.
flags.DEFINE_bool("macrobench", False, "Plot macrobenchmark results")
flags.DEFINE_string(
    "macrobench_dir",
    "./macrobench/data",
    "Location of macrobenchmark data. If the folder corresponding to each experiment does not contain a .csv file, it will be automatically generated",
)

# Whether or not to save data as interactive HTML files and where to save it.
flags.DEFINE_bool("save_plots", False, "Save plots as interactive HTML files")
flags.DEFINE_string("save_dir", "./figures", "Directory where to save plots")

# Whether or not to include speedup information in output.
flags.DEFINE_bool("print_speedup", False, "Print the speedup over unsafe")

# Flags related to automatic config detection.
flags.DEFINE_string(
    "generate_script",
    "microbench/experiment_list_generate.sh",
    "Script used to generate experiments that is examined when detecting the configuration.",
)
flags.DEFINE_string(
    "runscript",
    "microbench/runscript.sh",
    "Script used to run experiments that includes additional configuration info.",
)
flags.DEFINE_bool(
    "autodetect",
    True,
    "Automatically derives all plot configuration information from the config files",
)
flags.DEFINE_bool(
    "detect_threads",
    False,
    "Automatically detects the maximum number of threads and thread incrment from config.mk",
)
flags.DEFINE_bool(
    "detect_experiments",
    False,
    "Automatically pull data structure and max key configurations from experiment_list_generate.sh",
)
flags.DEFINE_bool(
    "detect_trials",
    False,
    "Automatically pull number of trials information from runscript.sh",
)

flags.DEFINE_integer(
    "workloads_rqrate",
    10,
    "Rate of range query operations to use when plotting the 'workloads' experiment",
)
flags.DEFINE_list(
    "workloads_urates",
    [0, 2, 10, 50, 90, 100],
    "Rate of range query operations to use when plotting the 'workloads' experiment",
)
flags.DEFINE_integer(
    "rqsize_maxkey", 100000, "Maximum key used when running the 'rq_size' experiment"
)
flags.DEFINE_integer(
    "rqsizes_numrqthreads",
    24,
    "Number of dedicated RQ threads used in the 'rqthreads' experiment",
)
flags.DEFINE_list(
    "rqsizes_rqsizes",
    [8, 64, 256, 1024, 8092, 16184],
    "Range query sizes to be used in the 'rqthreads' experiment",
)

flags.DEFINE_list("experiments", None, "List of experiments to plot")
flags.DEFINE_list("datastructures", None, "List of data structures to plot")
flags.DEFINE_list("max_keys", None, "List of max keys to use while plotting")
flags.DEFINE_list("nthreads", None, "List of thread counts to plot")
flags.DEFINE_integer(
    "ntrials", 3, "Number of trials per experiment (used for averaging results)"
)

flags.DEFINE_bool("legends", True, "Whether to show legends in the plots")
flags.DEFINE_bool(
    "yaxis_titles", True, "Whether to include y-axis titles in the plots"
)


def plot_workload(
    dirpath,
    ds,
    max_key,
    u_rate,
    rq_rate,
    threads,
    ntrials,
    ylabel=False,
    legend=False,
    save=False,
    save_dir="",
):
    """ Generates a plot showing throughput as a function of number of threads
        for the given data structure. 
        
    Arguments:
        dirpath: A string indicating where the data to plot lives.
        ds: The name of the data structure to plot.
        max_key: The configured size for the run to plot.
        u_rate: Update rate of the run to plot.
        rq_rate: RQ rate of the run to plot.
        threads: An array of thread counts for the x-axis.
        ntrials: Number of trials used to generate data.
        ylabel: Whether or not to include label on y-axis
        legend: Whether or not to include legend.
        save: Whether or not to save plots to disk.
        save_dir: Where plots are saved to.
    """
    reset_base_config()
    csvfile = CSVFile.get_or_gen_csv(os.path.join(dirpath, "workloads"), ds, ntrials)
    csv = CSVFile(csvfile)

    # Provide column labels for desired x and y axis
    x_axis = "wrk_threads"
    y_axis = "tot_thruput"

    # Init data store
    data = {}

    # Ignores rows in .csv with the following label
    ignore = ["ubundle"]
    algos = [k for k in plotconfig.keys() if k not in ignore]

    # Read in data for each algorithm
    count = 0
    data = csv.getdata(["max_key", "u_rate", "rq_rate"], [max_key, u_rate, rq_rate])
    data[y_axis] = data[y_axis] / 1000000

    if data.empty:
        print("No data: (ds={}, max_key={}, u_rate={})".format(ds, max_key, u_rate))
        return  # If no data to plot, then don't

    # Plot layout configuration.
    x_axis_layout_["title"] = None
    x_axis_layout_["tickfont"]["size"] = 52
    x_axis_layout_["nticks"] = len(threads)
    if ylabel:
        y_axis_layout_["title"]["text"] = "Mops/s"
        y_axis_layout_["title"]["font"]["size"] = 50
        y_axis_layout_["title"]["standoff"] = 50
    else:
        y_axis_layout_["title"] = None
    y_axis_layout_["tickfont"]["size"] = 50
    y_axis_layout_["nticks"] = 5
    legend_layout_ = (
        # {"font": legend_font_, "orientation": "h", "x": 0, "y": 1} if legend else {}
        {"font": legend_font_, "orientation": "v", "x": 1.1, "y": 1} if legend else {}
    )
    layout_["legend"] = legend_layout_
    layout_["autosize"] = False
    layout_["width"] = 800 if legend else 560
    layout_["height"] = 450

    fig = go.Figure(layout=layout_)
    for a in algos:
        symbol_ = plotconfig[a]["symbol"]
        color_ = update_opacity(plotconfig[a]["color"], 1)
        marker_ = {
            "symbol": symbol_,
            "color": color_,
            "size": 25,
            "line": {"width": (2 if legend else 5), "color": "black"},
        }
        line_ = {"width": 7}
        name_ = "<b>" + plotconfig[a]["label"] + "</b>"
        y_ = data[data["list"] == ds + "-" + a]
        y_ = y_[y_.wrk_threads.isin(threads)]["tot_thruput"]
        fig.add_scatter(
            x=threads, y=y_, name=name_, marker=marker_, line=line_, showlegend=legend,
        )

    if not save:
        fig.show()
    else:
        save_dir = os.path.join(save_dir, "workloads/" + ds)
        os.makedirs(save_dir, exist_ok=True)
        filename = (
            "update"
            + str(u_rate)
            + "_rq"
            + str(rq_rate)
            + "_maxkey"
            + str(max_key)
            + ".html"
        )
        fig.write_html(os.path.join(save_dir, filename))

    # Print speedup for paper.
    if FLAGS.print_speedup:
        ignore = ["ubundle"]
        overalgo = "rlu"
        overalgos = [
            k for k in plotconfig.keys() if (k not in ignore and k != overalgo)
        ]
        print(
            'Speedup over "'
            + overalgo
            + '" for '
            + ds
            + " @ "
            + str(u_rate)
            + "% updates\n"
        )
        threads_printed = False
        for o in overalgos:
            o_name = ds + "-" + o
            if not threads_printed:
                print("{:<15}|".format("algorithm"), end="")
                for i in range(len(threads) // 2):
                    print("{:10}".format(""), end="")
                print("# threads")
                print("{:15}|".format("---------------"), end="")
                for i in range(len(threads)):
                    print("{:10}".format("----------"), end="")
                print()
                print("{:<15}|".format(""), end="")
                for t in threads:
                    print("{:>10}".format(t), end="")
                print()
                print("{:<15}|".format(""), end="")
                for t in threads:
                    print("{:>10}".format("-----"), end="")
                threads_printed = True

            if len(threads) == 0:
                continue
            print("\n{:15}|".format(""))
            print("{:<15}{}".format(o, "|"), end="")
            for t in threads:
                numerator = data[data["list"] == o_name]
                numerator = numerator[numerator["wrk_threads"] == t]["tot_thruput"]
                denominator = data[data["list"] == ds + "-" + overalgo]
                denominator = denominator[denominator["wrk_threads"] == t][
                    "tot_thruput"
                ]
                try:
                    print(
                        "{:>10.3}".format(numerator.values[0] / denominator.values[0]),
                        end="",
                    )
                except:
                    print(
                        "{:>10}".format("-"), end="",
                    )
        print("\n\n")


def plot_rq_sizes(
    dirpath,
    ds,
    max_key,
    ntrials,
    rqsizes,
    ylabel=False,
    legend=False,
    save=False,
    save_dir="",
):
    reset_base_config()
    csv_path = os.path.join(dirpath, "rq_sizes")
    csv_file = CSVFile.get_or_gen_csv(csv_path, ds, ntrials)
    csv = CSVFile(csv_file)

    x_axis = "rq_size"
    y_axes = ["u_thruput", "rq_thruput"]

    ignore = ["ubundle"]
    algos = [k for k in plotconfig.keys() if k not in ignore]

    count = 0
    data = csv.getdata(
        ["max_key", "rq_threads"], [max_key, FLAGS.rqsizes_numrqthreads]
    )
    # Normalize
    for y_axis in y_axes:
        data[y_axis] = data[y_axis] / 1000000

    if data.empty:
        print("No data: (ds={}, max_key={})".format(ds, max_key))
        return  # If no data to ploy, then don't

    # Plot layout configuration.
    legend_layout_ = (
        {"font": legend_font_, "orientation": "v", "x": 1.15, "y": 1} if legend else {}
    )
    layout_["legend"] = legend_layout_
    layout_["autosize"] = False
    layout_["width"] = 1260
    layout_["height"] = 450

    # fig = go.Figure(layout=layout_)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1)
    fig.update_layout(layout_)
    fig.update_xaxes(
        title_text=None,
        tickfont=axis_font_,
        title_font=axis_font_,
        tickfont_size=32,
        tickangle=30,
        tickformat=".0f",
        nticks=len(rqsizes),
        zerolinecolor="black",
        gridcolor="black",
        gridwidth=2,
        linecolor="black",
        linewidth=4,
        mirror=True,
        type="log",
        dtick=math.log10(4),
    )
    fig.update_yaxes(
        tickfont=axis_font_,
        title_font=axis_font_,
        title_standoff=50,
        nticks=3,
        title_font_size=32,
        tickfont_size=32,
        zerolinecolor="black",
        gridcolor="black",
        gridwidth=2,
        linecolor="black",
        linewidth=4,
        mirror=True,
    )
    fig.update_yaxes(title_text="Mops/s", col=1, row=1)
    # fig.update_yaxes(title_text="RQ Mops/s", col=2, row=1)
    for y_axis, i in zip(y_axes, range(0, len(y_axes))):
        for a in algos:
            symbol_ = plotconfig[a]["symbol"]
            color_ = update_opacity(plotconfig[a]["color"], 1)
            marker_ = {
                "symbol": symbol_,
                "color": color_,
                "size": 25,
                "line": {"width": 5, "color": "black"},
            }
            line_ = {"width": 7}
            name_ = "<b>" + plotconfig[a]["label"] + "</b>"
            x_ = rqsizes
            y_ = data[data["list"] == ds + "-" + a]
            y_ = y_[y_.rq_size.isin(rqsizes)][y_axis]
            fig.add_scatter(
                x=x_,
                y=y_,
                name=name_,
                marker=marker_,
                line=line_,
                showlegend=(legend if i == 0 else False),
                legendgroup=a,
                row=1,
                col=i + 1,
            )

    if not save:
        fig.show()
    else:
        save_dir = os.path.join(save_dir, "rq_sizes/" + ds)
        os.makedirs(save_dir, exist_ok=True)
        filename = (
            "nrqthreads"
            + str(FLAGS.rqsizes_numrqthreads)
            + "_maxkey"
            + str(max_key)
            + ".html"
        )
        fig.write_html(os.path.join(save_dir, filename))


def plot_macrobench(dirpath, ds, ylabel=False, legend=False, save=False, save_dir=""):
    if not os.path.exists(os.path.join(dirpath, "data.csv")):
        subprocess.call(
            "./macrobench/make_csv.sh "
            + os.path.join(dirpath, "summary.txt")
            + " "
            + os.path.join(dirpath, "data.csv"),
            shell=True,
        )

    xaxis = "nthreads"
    yaxis = "ixThroughput"
    reset_base_config()
    csv = CSVFile(os.path.join(dirpath, "data.csv"))
    data = csv.getdata(["datastructure"], [ds])
    data[yaxis] = data[yaxis] / 1000000  # Normalizes throughput.

    ignore = ["rwlock"]
    algos = [k for k in plotconfig.keys() if k not in ignore]

    if FLAGS.print_speedup:
        print("-----" + ds + "-----")
        print(data["nthreads"].unique())
        overalgo = plotconfig["unsafe"]["macrobench"]
        for a in algos:
            print(a)
            try:
                numerator = data[data["rqalg"] == plotconfig[a]["macrobench"]]
                numerator = numerator[yaxis]
                denominator = data[data["rqalg"] == overalgo]
                denominator = denominator[yaxis]
                newvals = numerator.values / denominator.values
                print(newvals)
                print("AVG: " + str(pandas.DataFrame(newvals).mean().values))
                print(
                    "AVG (multithreaded-only): "
                    + str(pandas.DataFrame(newvals[1:]).mean().values)
                )
            except:
                print("-")

    x_axis_layout_["title"] = None
    x_axis_layout_["tickfont"]["size"] = 52
    y_axis_layout_["nticks"] = 6
    y_axis_layout_["tickfont"]["size"] = 52
    y_axis_layout_["range"] = [-10, 60]
    if ylabel:
        y_axis_layout_["title"]["text"] = "Mops/s"
        y_axis_layout_["title"]["font"]["size"] = 50
    else:
        y_axis_layout_["title"] = None
    legend_layout_ = (
        {"font": legend_font_, "orientation": "h", "x": 0, "y": 1.15} if legend else {}
    )
    # legend_layout_['font']['size'] = 40
    layout_["legend"] = legend_layout_
    layout_["width"] = 700 if legend else 560
    layout_["height"] = 450 if legend else 400

    fig = go.Figure(layout=layout_)
    for algo in algos:
        symbol_ = plotconfig[algo]["symbol"]
        line_ = {"width": 7, "color": plotconfig[algo]["color"]}
        opacity_ = 1
        x_ = data[data["rqalg"] == plotconfig[algo]["macrobench"]][xaxis]
        y_ = data[data["rqalg"] == plotconfig[algo]["macrobench"]][yaxis]
        marker_ = {
            "symbol": symbol_,
            "opacity": opacity_,
            "size": 25,
            "line": {"color": "black", "width": 5 if not legend else 3},
        }
        name_ = "<b>" + plotconfig[algo]["label"] + "</b>"
        fig.add_trace(
            go.Scatter(
                x=x_,
                y=y_,
                name=name_,
                mode="markers+lines",
                marker=marker_,
                line=line_,
                showlegend=legend,
            )
        )

        # Uncommenting below and commenting above will include fewer points on the plot
        # fig.add_trace(go.Scatter(
        #     x=x_[0::2], y=y_[0::2], name=name_, mode='markers+lines', marker=marker_, line=line_, showlegend=legend))

    if not save:
        fig.show()
    else:
        filename = ds + ".html"
        fig.write_html(os.path.join(save_dir, filename))


def get_threads_config():
    nthreads = []
    if FLAGS.detect_threads:
        print('Automatically deriving thread configuration from "./config.mk"...')
        nthreads.append(1)
        threads_config = parse_config("./config.mk")
        for i in range(
            threads_config["threadincrement"],
            threads_config["maxthreads"],
            threads_config["threadincrement"],
        ):
            nthreads.append(i)
        nthreads.append(threads_config["maxthreads"])
    else:
        assert FLAGS.nthreads is not None
        for n in FLAGS.nthreads:
            nthreads.append(int(n))
    return nthreads


def get_microbench_configs():
    if FLAGS.detect_experiments:
        print("Automatically detecting microbenchmark configurations")
        return parse_experiment_list_generate(
            FLAGS.generate_script, ["run_workloads", "run_rq_sizes"],
        )
    else:
        experiments = FLAGS.experiments
        experiment_configs = {}
        experiment_configs["datastructures"] = FLAGS.datastructures
        experiment_configs["ksizes"] = [int(max_key) for max_key in FLAGS.max_keys]
        return experiments, experiment_configs


def main(argv):
    # If autodetect flag is set, then detect all configs automatically
    if FLAGS.autodetect:
        FLAGS.detect_threads = True
        FLAGS.detect_experiments = True
        FLAGS.detect_trials = True

    # Plot microbench results.
    if FLAGS.microbench:
        assert FLAGS.microbench_dir is not None
        FLAGS.workloads_urates = [int(u) for u in FLAGS.workloads_urates]

        nthreads = get_threads_config()
        print("Thread configuration: " + str(nthreads))
        experiments, microbench_configs = get_microbench_configs()
        if FLAGS.datastructures is not None:
            microbench_configs["datastructures"] = FLAGS.datastructures
        if FLAGS.max_keys is not None:
            microbench_configs["ksizes"] = [int(k) for k in FLAGS.max_keys]
        print("Experiments to plot: " + str(experiments))
        print("Data structures and key ranges: " + str(microbench_configs))

        if FLAGS.detect_trials:
            runscript_config = parse_runscript(FLAGS.runscript, ["trials"])
            ntrials = runscript_config["trials"]
        else:
            ntrials = FLAGS.ntrials
        print("Number of trials: " + str(ntrials))

        # Plot peformance at different workload configurations (corresponds to Figure 2)
        for ds in microbench_configs["datastructures"]:
            for k in microbench_configs["ksizes"]:
                if "run_workloads" in experiments:
                    for u in FLAGS.workloads_urates:
                        plot_workload(
                            FLAGS.microbench_dir,
                            ds,
                            k,
                            u,
                            (FLAGS.workloads_rqrate if u != 100 else 0),
                            nthreads,
                            ntrials,
                            FLAGS.yaxis_titles,
                            FLAGS.legends,
                            FLAGS.save_plots,
                            os.path.join(FLAGS.save_dir, "microbench"),
                        )

                if "run_rq_sizes" in experiments:
                    plot_rq_sizes(
                        FLAGS.microbench_dir,
                        ds,
                        k,
                        ntrials,
                        FLAGS.rqsizes_rqsizes,
                        FLAGS.yaxis_titles,
                        FLAGS.legends,
                        FLAGS.save_plots,
                        os.path.join(FLAGS.save_dir, "microbench"),
                    )

    # Plot macrobench results (corresponds to Figure 4)
    if FLAGS.macrobench:
        save_dir = os.path.join(FLAGS.save_dir, "macrobench/skiplistlock")
        os.makedirs(save_dir, exist_ok=True)
        plot_macrobench(
            os.path.join(FLAGS.macrobench_dir, "rq_tpcc"),
            "SKIPLISTLOCK",
            ylabel=FLAGS.yaxis_titles,
            legend=FLAGS.legends,
            save=FLAGS.save_plots,
            save_dir=save_dir,
        )
        save_dir = os.path.join(FLAGS.save_dir, "macrobench/citrus")
        os.makedirs(save_dir, exist_ok=True)
        plot_macrobench(
            os.path.join(FLAGS.macrobench_dir, "rq_tpcc"),
            "CITRUS",
            ylabel=FLAGS.yaxis_titles,
            legend=FLAGS.legends,
            save=FLAGS.save_plots,
            save_dir=save_dir,
        )


if __name__ == "__main__":
    app.run(main)

