import numpy as np
import plotly
import plotly.graph_objects as go
from plotly import subplots
from plot_util import *

# from plot_config import *
import argparse
from plotly.subplots import make_subplots
import math
from absl import app
from absl import flags

FLAGS = flags.FLAGS

# General configuration flags
flags.DEFINE_bool("microbench", False, "Plot microbenchmark results")
flags.DEFINE_string(
    "microbench_dir",
    "./microbench/data",
    "Location of microbenchmark data. If the folder corresponding to each experiment does not contain a .csv file, it will be automatically generated",
)
flags.DEFINE_bool("macrobench", False, "Plot macrobenchmark results")
flags.DEFINE_string(
    "macrobench_dir",
    "./macrobench/data",
    "Location of macrobenchmark data. If the folder corresponding to each experiment does not contain a .csv file, it will be automatically generated",
)
flags.DEFINE_bool("save_plots", False, "Save plots as interactive HTML files")
flags.DEFINE_string("save_dir", "./figures", "Directory where to save plots")
flags.DEFINE_bool("print_speedup", False, "Print the speedup over unsafe")

# Flags related to automatic detection of configuration
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
    "rqsizes_maxkey", 100000, "Maximum key used when running the 'rqsizes' experiment"
)
flags.DEFINE_integer(
    "rqthreads_numrqthreads",
    36,
    "Number of dedicated RQ threads used in the 'rqthreads' experiment",
)
flags.DEFINE_list("experiments", None, "List of experiments to plot")
flags.DEFINE_list("datastructures", None, "List of data structures to plot")
flags.DEFINE_list("max_keys", None, "List of max keys to use while plotting")
flags.DEFINE_list("nthreads", None, "List of thread counts to plot")
flags.DEFINE_integer(
    "ntrials", 3, "Number of trials per experiment (used for averaging results)"
)

flags.re


def plot_workload(
    dirpath,
    ds,
    max_key,
    u_rate,
    rq_rate,
    ntrials,
    ylabel=False,
    legend=False,
    save=False,
    save_dir="",
):
    """ Generates a plot showing throughput as a function of number of threads
        for the given data structure. """
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
    for a in algos:
        data[a] = {}
        data[a] = csv.getdata(
            x_axis,
            y_axis,
            ["list", "max_key", "u_rate", "rq_rate"],
            [ds + "-" + a, max_key, u_rate, rq_rate],
        )
        count += len(data[a]["x"])
        data[a]["y"] = data[a]["y"] / 1000000  # Normalize data

    if count == 0:
        print("No data at given key range: ({}, {})".format(ds, max_key))
        return  # If no data to ploy, then don't

    # Plot layout configuration.
    x_axis_layout_["title"] = None
    x_axis_layout_["tickfont"]["size"] = 52
    x_axis_layout_["nticks"] = 6
    if ylabel:
        y_axis_layout_["title"]["text"] = "Mops/s"
        y_axis_layout_["title"]["font"]["size"] = 50
    else:
        y_axis_layout_["title"] = None
    y_axis_layout_["tickfont"]["size"] = 52
    y_axis_layout_["nticks"] = 5
    legend_layout_ = (
        {"font": legend_font_, "orientation": "v", "x": 0, "y": 1.15} if legend else {}
    )
    layout_["legend"] = legend_layout_
    layout_["autosize"] = False
    layout_["width"] = 750
    layout_["height"] = 550

    fig = go.Figure(layout=layout_)
    for a in algos:
        symbol_ = plotconfig[a]["symbol"]
        color_ = update_opacity(plotconfig[a]["color"], 1)
        marker_ = {
            "symbol": symbol_,
            "color": color_,
            "size": 40,
            "line": {"width": 5, "color": "black"},
        }
        line_ = {"width": 10}
        name_ = "<b>" + plotconfig[a]["label"] + "</b>"
        fig.add_scatter(
            x=data[a]["x"],
            y=data[a]["y"],
            name=name_,
            marker=marker_,
            line=line_,
            showlegend=legend,
        )

        # Comment the above line and uncomment below to show fewer points per plot.
        # fig.add_scatter(x=data[a]['x'][0::2], y=data[a]['y'][0::2], name=name_,
        #                 marker=marker_, line=line_, showlegend=legend)

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
        overalgo = "unsafe"
        overalgos = [
            k for k in plotconfig.keys() if (k not in ignore and k != overalgo)
        ]
        print('Speedup over "unsafe" for ' + ds + " @ " + str(u_rate) + "% updates\n")
        threads_printed = False
        for o in overalgos:
            if not threads_printed:
                print("{:<15}|".format("algorithm"), end="")
                for i in range(len(data[o]["x"]) // 2):
                    print("{:10}".format(""), end="")
                print("# threads")
                print("{:15}|".format("---------------"), end="")
                for i in range(len(data[o]["x"])):
                    print("{:10}".format("----------"), end="")
                print()
                print("{:<15}|".format(""), end="")
                for t in data[o]["x"]:
                    print("{:>10}".format(t), end="")
                print()
                print("{:<15}|".format(""), end="")
                for t in data[o]["x"]:
                    print("{:>10}".format("-----"), end="")
                threads_printed = True

            if len(data[o]["x"]) == 0:
                continue
            print("\n{:15}|".format(""))
            print("{:<15}{}".format(o, "|"), end="")
            for i in range(0, len(data[o]["x"])):
                print(
                    "{:>10.3}".format(data[o]["y"][i] / data[overalgo]["y"][i]), end=""
                )
        print("\n\n")


def plot_rq_sizes(
    dirpath,
    dss,
    max_key,
    nthreads,
    ntrials,
    ylabel=False,
    legend=False,
    save=False,
    save_dir="",
):
    # Experiment 1 demonstrates performance as the workload distribution changes.

    # Create the required .csv files if there are none, then plot the data structure.

    reset_base_config()
    x_axis = "rq_size"
    y_axis = "tot_thruput"
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    ignore = ["ubundle"]
    algos = [k for k in plotconfig.keys() if k not in ignore]
    count = 0
    for ds in dss:
        csvfile = CSVFile.get_or_gen_csv(os.path.join(dirpath, "rq_sizes"), ds, ntrials)
        csv = CSVFile(csvfile)
        data[ds] = {}
        for algo in algos:
            data[ds][algo] = {}
            for t in nthreads:
                data[ds][algo][t] = csv.getdata(
                    x_axis,
                    y_axis,
                    ["list", "max_key", "wrk_threads"],
                    [ds + "-" + algo, max_key, t],
                )
                count += len(data[ds][algo][t])

    if count == 0:
        print("No data found for rqsizes")
        return

    # Calculate speedup.
    speedup = {}
    overalgo = "unsafe"
    for ds in dss:
        speedup[ds] = {}
        for algo in algos:
            if algo == overalgo:
                continue
            speedup[ds][algo] = {}
            for t in nthreads:
                speedup[ds][algo][t] = {}
                if data[ds][algo][t]["y"].size == 0:
                    speedup[ds][algo][t]["x"] = []
                    speedup[ds][algo][t]["y"] = []
                    continue
                speedup[ds][algo][t]["x"] = data[ds][overalgo][t]["x"]
                try:
                    speedup[ds][algo][t]["y"] = (
                        data[ds][algo][t]["y"] / data[ds][overalgo][t]["y"]
                    )
                except:
                    shape_ = data[ds][overalgo][t]["y"].shape
                    speedup[ds][algo][t]["y"] = np.zeros(shape=shape_)
                # speedup[algo][rq_size]['y'] =  data['lbundle'][rq_size]['y'][::2] / data[algo][rq_size]['y'][::2]

    # Plot speedup.
    x_axis_layout_["showgrid"] = False
    y_axis_layout_["dtick"] = 0.25

    legend_layout_ = (
        {
            "font": legend_font_,
            "orientation": "v",
            "x": 1.05,
            "y": 0.5,
            "traceorder": "grouped",
            "tracegroupgap": 0,
        }
        if legend
        else {}
    )

    reference_line_ = {
        "type": "line",
        "x0": -0.6,
        "y0": 1,
        "x1": len(nthreads) + 0.6,
        "y1": 1,
        "line": {"width": 8, "color": "black"},
        "layer": "below",
    }

    box1_ = {
        "type": "rect",
        "yref": "paper",
        "x0": 0.5,
        "x1": 1.5,
        "y0": 0,
        "y1": 1,
        "layer": "below",
        "line": {"width": 0},
        "fillcolor": "slategray",
        "opacity": 0.25,
    }
    box2_ = {
        "type": "rect",
        "yref": "paper",
        "x0": 2.5,
        "x1": 3.5,
        "y0": 0,
        "y1": 1,
        "layer": "below",
        "line": {"width": 0},
        "fillcolor": "slategray",
        "opacity": 0.25,
    }
    box3_ = {
        "type": "rect",
        "yref": "paper",
        "x0": 4.5,
        "x1": 5.5,
        "y0": 0,
        "y1": 1,
        "layer": "below",
        "line": {"width": 0},
        "fillcolor": "slategray",
        "opacity": 0.25,
    }

    layout_["shapes"] = [box1_, box2_, box3_]
    layout_["legend"] = legend_layout_
    layout_["height"] = 750
    layout_["width"] = 2200

    specs2_ = [[{"rowspan": len(dss)}, {}], [None, {}]]
    specs3_ = [[{"rowspan": len(dss)}, {}], [None, {}], [None, {}]]
    specs_ = None
    if len(dss) == 2:
        specs_ = specs2_
    elif len(dss) == 3:
        specs_ = specs3_
    fig = plotly.subplots.make_subplots(
        rows=len(dss),
        cols=2,
        column_widths=[0.15, 0.85],
        specs=specs_,
        shared_xaxes=True,
    )
    fig.update_xaxes(x_axis_layout_)
    fig.update_yaxes(y_axis_layout_)

    curr_row_ = 1
    for ds in dss:
        for algo in algos:
            if algo == overalgo:
                continue
            opacity_ = 1
            for t in nthreads:
                x_ = speedup[ds][algo][t]["x"]
                y_ = speedup[ds][algo][t]["y"]
                color_ = update_opacity(plotconfig[algo]["color"], opacity_)
                marker_ = {"color": color_, "line": {"width": 1.5, "color": "black"}}
                fig.add_bar(
                    x=x_,
                    y=y_,
                    marker=marker_,
                    name="<b>"
                    + plotconfig[algo]["label"]
                    + " (n="
                    + str(t)
                    + ", "
                    + ds
                    + ")</b>",
                    legendgroup=ds,
                    showlegend=legend,
                    row=curr_row_,
                    col=2,
                )
                opacity_ -= 1.0 / (len(nthreads) + 1)
                fig.update_yaxes(title_text=str(ds), row=curr_row_, col=2)
        curr_row_ += 1

    fig.update_xaxes(title_text="Range Query Size", row=len(dss), col=2)

    annotations_ = [
        dict(
            x=0,
            y=0.5,
            showarrow=False,
            text="Rel. Throughput",
            textangle=-90,
            font=axis_font_,
            xref="paper",
            yref="paper",
        )
    ]
    fig.update_layout(layout_)
    fig.update_layout(
        barmode="group", bargap=0.05, bargroupgap=0.01, annotations=annotations_
    )

    if not save:
        fig.show()
    else:
        filename = "rqsize_maxkey" + str(max_key) + ".html"
        subdir = os.path.join(save_dir, "rqsizes")
        fig.write_html(os.path.join(subdir, filename))


def plot_rq_threads(
    dirpath, ds, max_key, ntrials, ylabel=False, legend=False, save=False, save_dir=""
):
    reset_base_config()
    csv_path = os.path.join(dirpath, "rq_threads")
    csv_file = CSVFile.get_or_gen_csv(csv_path, ds, ntrials)
    csv = CSVFile(csv_file)

    x_axis = "rq_size"
    y_axes = ["u_thruput", "rq_thruput"]

    ignore = ["ubundle"]
    algos = [k for k in plotconfig.keys() if k not in ignore]

    count = 0
    data = {}
    for y_axis in y_axes:
        data[y_axis] = {}
        for a in algos:
            data[y_axis][a] = {}
            data[y_axis][a] = csv.getdata(
                x_axis,
                y_axis,
                ["list", "max_key", "rq_threads"],
                [ds + "-" + a, max_key, FLAGS.rqthreads_numrqthreads],
            )
            count += len(data[y_axis][a]["x"])
            data[y_axis][a]["y"] = (
                data[y_axis][a]["y"] / 1000000
            )  # Normalize data to Mops

    if count == 0:
        print("No data: ({}, {})".format(ds, max_key))
        return  # If no data to ploy, then don't

    # Plot layout configuration.
    x_axis_layout_["title"] = None
    x_axis_layout_["tickfont"]["size"] = 52
    x_axis_layout_["nticks"] = 6
    if ylabel:
        y_axis_layout_["title"]["text"] = "Mops/s"
        y_axis_layout_["title"]["font"]["size"] = 50
    else:
        y_axis_layout_["title"] = None
    y_axis_layout_["tickfont"]["size"] = 52
    y_axis_layout_["nticks"] = 5
    legend_layout_ = (
        {"font": legend_font_, "orientation": "v", "x": 0, "y": 1.15} if legend else {}
    )
    layout_["legend"] = legend_layout_
    layout_["autosize"] = False
    layout_["width"] = 750
    layout_["height"] = 550

    # fig = go.Figure(layout=layout_)
    fig = make_subplots(rows=1, cols=2)
    # fig.update_layout(layout_)
    for y_axis, i in zip(y_axes, range(0, len(y_axes))):
        for a in algos:
            symbol_ = plotconfig[a]["symbol"]
            color_ = update_opacity(plotconfig[a]["color"], 1)
            marker_ = {
                "symbol": symbol_,
                "color": color_,
                "size": 40,
                "line": {"width": 5, "color": "black"},
            }
            line_ = {"width": 10}
            name_ = "<b>" + plotconfig[a]["label"] + "</b>"
            fig.add_scatter(
                x=data[y_axis][a]["x"],
                y=data[y_axis][a]["y"],
                name=name_,
                marker=marker_,
                line=line_,
                showlegend=legend,
                row=1,
                col=i + 1,
            )

            # Comment the above line and uncomment below to show fewer points per plot.
            # fig.add_scatter(x=data[a]['x'][0::2], y=data[a]['y'][0::2], name=name_,
            #                 marker=marker_, line=line_, showlegend=legend)

    fig.update_xaxes(type="log", dtick=math.log10(2))

    if not save:
        fig.show()
    else:
        save_dir = os.path.join(save_dir, "rq_threads/" + ds)
        os.makedirs(save_dir, exist_ok=True)
        filename = (
            "nrqthreads"
            + str(FLAGS.rqthreads_numrqthreads)
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

    reset_base_config()
    csv = CSVFile(os.path.join(dirpath, "data.csv"))
    data = {}
    for algo in plotconfig.keys():
        data[algo] = csv.getdata(
            "nthreads",
            "ixThroughput",
            ["rqalg", "datastructure"],
            [plotconfig[algo]["macrobench"], ds],
        )
        data[algo]["y"] = data[algo]["y"] / 1000000  # Normalizes throughput.

    speedup = {}
    overalgo = "unsafe"
    for algo in plotconfig.keys():
        if algo == overalgo:
            continue
        speedup[algo] = {}
        if data[algo]["y"].size == 0:
            speedup[algo]["x"] = []
            speedup[algo]["y"] = []
            continue
        speedup[algo]["x"] = data[overalgo]["x"][::2]
        try:
            speedup[algo]["y"] = data[algo]["y"][::2] / data[overalgo]["y"][::2]
        except:
            shape_ = data[overalgo]["y"][::2].shape
            speedup[algo]["y"] = np.zeros(shape=shape_)

    x_axis_layout_["title"] = None
    x_axis_layout_["tickfont"]["size"] = 52
    y_axis_layout_["nticks"] = 6
    y_axis_layout_["tickfont"]["size"] = 52
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
    layout_["width"] = 750
    if legend:
        layout_["height"] = 750
    else:
        layout_["height"] = 350

    fig = go.Figure(layout=layout_)
    for algo in plotconfig.keys():
        symbol_ = plotconfig[algo]["symbol"]
        line_ = {"width": 10, "color": plotconfig[algo]["color"]}
        opacity_ = 1
        x_ = data[algo]["x"]
        y_ = data[algo]["y"]
        marker_ = {
            "symbol": symbol_,
            "opacity": opacity_,
            "size": 40,
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
            nthreads += int(n)
    return nthreads


def get_microbench_configs():
    if FLAGS.detect_experiments:
        print("Automatically detecting microbenchmark configurations")
        return parse_experiment_list_generate(
            "./microbench/experiment_list_generate.sh",
            ["run_workloads", "run_rq_sizes", "run_rq_threads"],
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
        print("Experiments to plot: " + str(experiments))
        print("Data structures and key ranges: " + str(microbench_configs))

        if FLAGS.detect_trials:
            runscript_config = parse_runscript("./microbench/runscript.sh", ["trials"])
            ntrials = runscript_config["trials"]
        else:
            ntrials = FLAGS.ntrials
        print("Number of trials: " + str(ntrials))

        # Plot peformance at different workload configurations (corresponds to Figure 2)
        for ds in microbench_configs["datastructures"]:
            for k in microbench_configs["ksizes"]:
                if "run_workloads" in experiments:
                    for u in FLAGS.workloads_urates:
                        print("Plotting workloads")
                        plot_workload(
                            FLAGS.microbench_dir,
                            ds,
                            k,
                            u,
                            (FLAGS.workloads_rqrate if u != 100 else 0),
                            ntrials,
                            True,
                            True,
                            FLAGS.save_plots,
                            os.path.join(FLAGS.save_dir, "microbench"),
                        )
                        pass

                if "run_rq_threads" in experiments:
                    print("Plotting rq_threads")
                    plot_rq_threads(
                        FLAGS.microbench_dir,
                        ds,
                        k,
                        ntrials,
                        True,
                        True,
                        FLAGS.save_plots,
                        os.path.join(FLAGS.save_dir, "microbench"),
                    )

        # Plot performance w.r.t. range query size experiments at 50% updates and 50% range queries (corresponds to Figure 3)
        if "run_rq_sizes" in experiments:
            if FLAGS.rqsize_maxkey not in microbench_configs["ksizes"]:
                print(
                    'Could not match key range to configuration derived from "./microbench/experiment_list_generate.sh"'
                )
            plot_rq_sizes(
                FLAGS.microbench_dir,
                microbench_configs["datastructures"],
                FLAGS.rqsize_maxkey,
                nthreads,
                ntrials,
                True,
                True,
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
            ylabel=True,
            legend=True,
            save=FLAGS.save_plots,
            save_dir=save_dir,
        )
        save_dir = os.path.join(FLAGS.save_dir, "macrobench/citrus")
        os.makedirs(save_dir, exist_ok=True)
        plot_macrobench(
            os.path.join(FLAGS.macrobench_dir, "rq_tpcc"),
            "CITRUS",
            ylabel=True,
            legend=True,
            save=FLAGS.save_plots,
            save_dir=save_dir,
        )


if __name__ == "__main__":
    app.run(main)

