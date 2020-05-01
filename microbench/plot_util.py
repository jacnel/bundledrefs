import pandas
import os
import subprocess

# General configuration.
dsconfig = {'lazylist': {'max_keys': [10000]}, 'skiplistlock': {
    'max_keys': [100000, 1000000]}, 'citrus': {'max_keys': [100000, 1000000]}}
algorithms = ['lbundle', 'lockfree', 'rwlock', 'rlu', 'unsafe']
max_keys = [10000, 100000, 1000000]
ntrials = 1

# COLORS = ['rgb(31, 119, 180)', 'rgb(255, 127, 14)',
#           'rgb(44, 160, 44)', 'rgb(214, 39, 40)',
#           'rgb(148, 103, 189)', 'rgb(140, 86, 75)',
#           'rgb(227, 119, 194)', 'rgb(127, 127, 127)',
#           'rgb(188, 189, 34)', 'rgb(23, 190, 207)']

COLORS = ['rgb(255,255,106)', 'rgb(31,120,180)', 'rgb(178,223,138)', 'rgb(51,160,44)', 'rgb(251,154,153)', 'rgb(207,233,252)',
          'rgb(188, 189, 34)', 'rgb(23, 190, 207)', 'rgb(23, 190, 207)', 'rgb(23, 190, 207)']

plotconfig = {
    'rwlock': {'label': 'EBR-RQ', 'color': COLORS[0], 'symbol': 1, 'macrobench': 'RQ_RWLOCK'},
    'lockfree': {'label': 'EBR-RQ-LF', 'color': COLORS[1], 'symbol': 0, 'macrobench': 'RQ_LOCKFREE'},
    'rlu': {'label': 'RLU', 'color': COLORS[4], 'symbol': 3, 'macrobench': 'RQ_RLU'},
    'lbundle': {'label': 'Bundle', 'color': COLORS[3], 'symbol': 2, 'macrobench': 'RQ_BUNDLE'},
    'ubundle': {'label': 'Bundle (fully relaxed)', 'color': COLORS[4], 'symbol': 5, 'macrobench': ''},
    'unsafe': {'label': 'Unsafe', 'color': COLORS[5], 'symbol': 4, 'macrobench': 'RQ_UNSAFE'},
}


def update_opacity(colorstr, opacity):
    temp = colorstr.split('(')
    return 'rgba(' + temp[1][:-1] + ', ' + str(opacity) + ')'


relaxconfig = {
    'relax1': {'label': 'T=1', 'color': COLORS[0], 'symbol': 1},
    'relax2': {'label': 'T=2', 'color': COLORS[1], 'symbol': 0},
    'relax5': {'label': 'T=5', 'color': COLORS[2], 'symbol': 3},
    # 'relax10': {'color': 'seagreen', 'symbol': 2},
    # 'relax20': {'color': 'darkorange', 'symbol': 5},
    'relax50': {'label': 'T=50', 'color': COLORS[3], 'symbol': 4},
    'relax100': {'label': 'T=100', 'color': COLORS[4], 'symbol': 6},
    'relax1k': {'label': 'T=1000', 'color': COLORS[5], 'symbol': 7},
    # 'relax10k': {'label': 'T=10000', 'color': COLORS[6], 'symbol': 8},
    'ubundle': {'label': 'T=infinity', 'color': COLORS[9], 'symbol': 9},
}

delayconfig = {
    'delay0': {'label': 'd=0ms', 'color': COLORS[0], 'symbol': 1},
    'delay1000': {'label': 'd=1ms', 'color': COLORS[1], 'symbol': 0},
    'delay5000': {'label': 'T=5ms', 'color': COLORS[2], 'symbol': 3},
    'delay10000': {'label': 'T=10ms', 'color': COLORS[3], 'symbol': 4},
    'delay100000': {'label': 'T=100ms', 'color': COLORS[4], 'symbol': 6},
    'nofree': {'label': 'Leaky', 'color': COLORS[5], 'symbol': 7}
}

rootdir = '/Users/jjn/Documents/Lehigh/sss/results/bundle/'
machine = 'luigi'
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
    axis_font_['family'] = 'Times-Roman'
    axis_font_['size'] = 72
    axis_font_['color'] = 'black'

    legend_font_['family'] = 'Times-Roman'
    legend_font_['size'] = 24
    legend_font_['color'] = 'black'

    x_axis_layout_['type'] = 'category'
    x_axis_layout_['title'] = {'text': ''}
    x_axis_layout_['title']['font'] = axis_font_.copy()
    x_axis_layout_['tickfont'] = axis_font_.copy()
    x_axis_layout_['zerolinecolor'] = 'black'
    x_axis_layout_['gridcolor'] = 'black'
    x_axis_layout_['gridwidth'] = 2
    x_axis_layout_['linecolor'] = 'black'
    x_axis_layout_['linewidth'] = 4
    x_axis_layout_['mirror'] = True

    y_axis_layout_['title'] = {'text': ''}
    y_axis_layout_['title']['font'] = axis_font_.copy()
    y_axis_layout_['tickfont'] = axis_font_.copy()
    y_axis_layout_['zerolinecolor'] = 'black'
    y_axis_layout_['gridcolor'] = 'black'
    y_axis_layout_['gridwidth'] = 2
    y_axis_layout_['linecolor'] = 'black'
    y_axis_layout_['linewidth'] = 4
    y_axis_layout_['mirror'] = True

    layout_['xaxis'] = x_axis_layout_
    layout_['yaxis'] = y_axis_layout_
    layout_['plot_bgcolor'] = 'white'


class CSVFile():
    """A wrapper class to read and manipulate data from output produced by make_csv.sh"""

    def __init__(self, filepath):
        self.df = pandas.read_csv(
            filepath, sep=",", engine="c", index_col=False)

    def __str__(self):
        return str(self.df.columns)

    def getdata(self, x_axis, y_axis, filter_col, filter_with):
        data = self.df.copy()  # Make a copy of the data frame to return.
        for o, w in zip(filter_col, filter_with):
            # Filter the data for the rows matching the column.
            data = data[data[o] == w]
        x = sorted(data[x_axis].unique())  # Get the unique x axis values
        y = data[y_axis].to_numpy()  # Get corresponding y values
        return {'x': x, 'y': y}

    # Tries to create a csv file for the given data structure (ds) and number of trials (n).
    @staticmethod
    def get_or_gen_csv(dirpath, ds, n):
        filepath = os.path.join(dirpath, ds + '.csv')
        if not os.path.exists(filepath):
            print('GENERATING .csv FILE FOR ' + ds + '...')
            subprocess.call('./make_csv.sh ' + dirpath + ' ' +
                            str(n) + ' ' + ds, shell=True)
        else:
            print('USING EXISTING .csv FILE')
        return filepath
