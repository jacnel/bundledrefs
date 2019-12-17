import pandas
import numpy as np
import plotly.graph_objects as go
from plot_config import *
import os


class Data():
    """A wrapper class to read and manipulate data from output produced by run.sh"""

    def __init__(self):
        self.rootdir = os.path.join(dirconfig["rootdir"], dirconfig["machine"])

    def read(self, filename, start):
        self.df = pandas.read_csv(
            filename, sep=",", header=start, engine="c", index_col=False)

    def __str__(self):
        return str(self.df.columns)

    def makeplot(self, algo, x_axis, y_axis, filter_on, filter_with, group_by, fig=None, color=None):
        data = self.df.copy()
        for o, w in zip(filter_on, filter_with):
            data = data[data[o] == w]
        if fig is None:
            layout = {}  # "title": str(filter_on)+"="+str(match)}
            fig = go.Figure(layout=layout)
        if group_by is not None:
            unique = sorted(data[group_by].unique())
            symbol = 0
            opacity = 1.0
            for u in unique:
                d_ = data[data[group_by] == u]
                x_ = sorted(d_[x_axis].unique())
                y_ = d_[y_axis].to_numpy()
                if color is not None:
                    line_ = {"color": color}
                else:
                    line_ = {"color": "royalblue"}
                marker_ = {"symbol": symbol, "opacity": opacity, "size": 16}
                symbol += 1
                opacity -= 1.0 / (len(unique) + 1)
                fig.add_trace(go.Scatter(x=x_, y=y_, mode="markers+lines",
                                         marker=marker_, name="("+algo+") "+group_by+"="+str(u), line=line_))
        else:
            d_ = data
            x_ = sorted(d_[x_axis].unique())
            y_ = d_[y_axis].to_numpy()
            if color is not None:
                line_ = {"color": color}
            else:
                line_ = {"color": "royalblue"}
            marker_ = {"size": 16}
            fig.add_trace(go.Scatter(x=x_, y=y_, mode="markers+lines",
                                     marker=marker_, name="("+list+")", line=line_))
        return fig

    def plot(self, p, ds):
        # Get configurations for given plot to produce and data structure.
        plotconfig = plots[p]
        dsconfig = datastructures[ds]

        # Read in data.
        datafile = os.path.join(self.rootdir, plotconfig["datadir"])
        datafile = os.path.join(datafile, dsconfig["filename"])
        self.read(filename=datafile, start=0)

        # Create and show plots for all y"s in configuration.
        for y in plotconfig["y"]:
            print("Creating plot... ("+plotconfig["title"]+", "+y+")")
            fig = None
            for a in algs.keys():
                filter_on = ['list']
                filter_with = [dsconfig['list'] + "-" + a]
                if 'group_by' in plotconfig:
                    group_by = plotconfig['group_by']
                else:
                    group_by = None
                for f in plotconfig['filter_on']:
                    assert(f in dsconfig.keys())
                    filter_on.append(f)
                    filter_with.append(dsconfig[f])
                fig = self.makeplot(
                    a, plotconfig['x'], y, filter_on, filter_with, group_by, fig, algs[a]['color'])
            fig.show()


if __name__ == "__main__":
    d = Data()
    # d.plot('exp0', 'citrus-smallrq')
    # d.plot('exp0', 'skiplist')
    # d.plot('exp0', 'citrus-largerq')
    # d.plot('exp1', 'skiplist')
    # d.plot('exp2', 'skiplist')
    d.plot('exp3', 'skiplist')
