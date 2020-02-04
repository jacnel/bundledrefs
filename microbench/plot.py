import pandas
import numpy as np
import plotly
import plotly.graph_objects as go
import os
import subprocess

# General configuration.
dsconfig = {'lazylist': {'max_keys': [10000]}, 'skiplistlock': {
    'max_keys': [100000, 1000000]}, 'citrus': {'max_keys': [100000, 1000000]}}
algorithms = ['lbundle', 'lockfree', 'rwlock', 'rlu', 'unsafe']
max_keys = [10000, 100000, 1000000]
ntrials = 3

COLORS = ['rgb(31, 119, 180)', 'rgb(255, 127, 14)',
          'rgb(44, 160, 44)', 'rgb(214, 39, 40)',
          'rgb(148, 103, 189)', 'rgb(140, 86, 75)',
          'rgb(227, 119, 194)', 'rgb(127, 127, 127)',
          'rgb(188, 189, 34)', 'rgb(23, 190, 207)']

plotconfig = {
    'rwlock': {'label': 'EBR-RQ', 'color': COLORS[0], 'symbol': 1, 'macrobench': 'RQ_RWLOCK'},
    'lockfree': {'label': 'EBR-RQ-LF', 'color': COLORS[1], 'symbol': 0, 'macrobench': 'RQ_LOCKFREE'},
    'rlu': {'label': 'RLU', 'color': COLORS[2], 'symbol': 3, 'macrobench': 'RQ_RLU'},
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

rootdir = '/home/jacob/sss/results/bundle/'
machine = 'luigi'
separate_unsafe = True

axis_font_ = {'family': 'Times-Roman',
              'size': 72, 'color': 'black'}
legend_font_ = {'family': 'Times-Roman',
                'size': 24, 'color': 'black'}

x_axis_layout_ = {'type': 'category', 'title': {'text': '',
                                                'font': axis_font_.copy()}, 'tickfont': axis_font_.copy(), 'linecolor': 'black', 'linewidth': 4, 'mirror': True}
y_axis_layout_ = {'title': {'text': '',
                            'font': axis_font_.copy()}, 'tickfont': axis_font_.copy(), 'gridcolor': 'black', 'gridwidth': 2, 'linecolor': 'black', 'linewidth': 4, 'mirror': True}
layout_ = {'xaxis': x_axis_layout_,
           'yaxis': y_axis_layout_,
           'plot_bgcolor': 'white'}

u_rates = [0, 10, 50, 90, 100]


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


def plot_exp0(dirpath, ds, max_key, ylabel=False, legend=False):
    # Experiment 1 demonstrates performance as the workload distribution changes.

    # Create the required .csv files if there are none, then plot the data structure.
    csvfile = ds + '.csv'
    if not os.path.exists(os.path.join(os.path.join(dirpath, 'exp0'), csvfile)):
        print('GENERATING .csv FILE FOR ' + ds + '...')
        subprocess.call('./make_csv.sh ' + os.path.join(dirpath, 'exp0') + ' ' +
                        str(ntrials) + ' ' + ds, shell=True)

    print('GENERATING PLOT FOR ' + ds + '...')
    csv = CSVFile(os.path.join(os.path.join(dirpath, 'exp0'), csvfile))
    x_axis = 'rq_size'
    y_axis = 'tot_thruput'
    nthreads = [24, 48, 96, 144, 192]
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    ignore = ['ubundle']
    algos = [k for k in plotconfig.keys() if k not in ignore]
    for algo in algos:
        data[algo] = {}
        for t in nthreads:
            data[algo][t] = csv.getdata(x_axis, y_axis, [
                'list', 'max_key', 'wrk_threads'], [ds + '-' + algo, max_key, t])

    # Calculate speedup.
    speedup = {}
    overalgo = 'unsafe'
    for algo in algos:
        if algo == overalgo:
            continue
        speedup[algo] = {}
        for t in nthreads:
            speedup[algo][t] = {}
            if data[algo][t]['y'].size == 0:
                speedup[algo][t]['x'] = []
                speedup[algo][t]['y'] = []
                continue
            speedup[algo][t]['x'] = data[overalgo][t]['x']
            try:
                speedup[algo][t]['y'] = data[algo][t]['y'] / \
                    data[overalgo][t]['y']
            except:
                shape_ = data[overalgo][t]['y'].shape
                speedup[algo][t]['y'] = np.zeros(shape=shape_)
            # speedup[algo][rq_size]['y'] =  data['lbundle'][rq_size]['y'][::2] / data[algo][rq_size]['y'][::2]

    # Plot speedup.
    x_axis_layout_['title']['text'] = 'Range Query Size'
    y_axis_layout_['title']['text'] = 'Relative Throughput' if ylabel else ''
    legend_layout_ = {'font': legend_font_,
                      'orientation': 'h', 'x': 0, 'y': 1.15, 'traceorder': 'grouped', 'tracegroupgap': 0} if legend else {}
    reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
                       'x1': len(nthreads)+0.6, 'y1': 1, 'line': {'width': 8, 'color': 'black'}, 'layer': 'below'}
    box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box3_ = {'type': 'rect', 'yref': 'paper', 'x0': 4.5, 'x1': 5.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    layout_['shapes'] = [reference_line_, box1_, box2_, box3_]
    layout_['legend'] = legend_layout_
    fig = go.Figure(layout=layout_)
    for algo in algos:
        if algo == overalgo:
            continue
        opacity_ = 1
        for t in nthreads:
            x_ = speedup[algo][t]['x']
            y_ = speedup[algo][t]['y']
            color_ = update_opacity(plotconfig[algo]['color'], opacity_)
            marker_ = {'color': color_, 'line': {
                'width': 1.5, 'color': 'black'}}
            fig.add_bar(x=x_, y=y_, marker=marker_,
                        name='<b>' + plotconfig[algo]['label'] + ' (n=' + str(t) + ')</b>', legendgroup=t, showlegend=legend)
            opacity_ -= 1.0 / (len(u_rates) + 1)
    fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
    fig.show()


def plot_exp1(dirpath, ds, max_key, ylabel=False, legend=False)
    # Experiment 1 demonstrates performance as the workload distribution changes.

    # Create the required .csv files if there are none, then plot the data structure.
    csvfile = ds + '.csv'
    if not os.path.exists(os.path.join(os.path.join(dirpath, 'exp1'), csvfile)):
        print('GENERATING .csv FILE FOR ' + ds + '...')
        subprocess.call('./make_csv.sh ' + os.path.join(dirpath, 'exp1') + ' ' +
                        str(ntrials) + ' ' + ds, shell=True)

    print('GENERATING PLOT FOR ' + ds + '...')
    csv = CSVFile(os.path.join(os.path.join(dirpath, 'exp1'), csvfile))
    x_axis = 'u_rate'
    y_axis = 'tot_thruput'
    nthreads = [24, 48, 96, 144, 192]
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    ignore = ['ubundle']
    algos = [k for k in plotconfig.keys() if k not in ignore]
    for algo in algos:
        data[algo] = {}
        for t in nthreads:
            data[algo][t] = csv.getdata(x_axis, y_axis, [
                'list', 'max_key', 'wrk_threads'], [ds + '-' + algo, max_key, t])

    # Plot results.

    # Calculate speedup.
    speedup = {}
    overalgo = 'lbundle'
    for algo in algos:
        if algo == overalgo:
            continue
        speedup[algo] = {}
        avgs = np.zeros(shape=len(data[overalgo][nthreads[0]]['x']))
        maxes = np.zeros(shape=len(data[overalgo][nthreads[0]]['x']))
        for t in nthreads:
            speedup[algo][t] = {}
            if data[algo][t]['y'].size == 0:
                speedup[algo][t]['x'] = []
                speedup[algo][t]['y'] = []
                continue
            speedup[algo][t]['x'] = data[overalgo][t]['x']
            try:
                speedup[algo][t]['y'] = data[overalgo][t]['y'] / \
                    data[algo][t]['y']
            except:
                shape_ = data[overalgo][t]['y'].shape
                speedup[algo][t]['y'] = np.zeros(shape=shape_)

            avgs += speedup[algo][t]['y']
            maxes = np.maximum(speedup[algo][t]['y'], maxes)
        print('avgs (' + algo + '): ' + str(avgs / len(nthreads)))
        print('maxes (' + algo + '): ' + str(maxes))

        # speedup[algo][rq_size]['y'] =  data['lbundle'][rq_size]['y'][::2] / data[algo][rq_size]['y'][::2]

    # Plot speedup.
    x_axis_layout_['title']['text'] = '% Updates'
    y_axis_layout_['title']['text'] = 'Relative Throughput' if ylabel else ''
    legend_layout_ = {'font': legend_font_,
                      'orientation': 'h', 'x': 0, 'y': 1.15} if legend else {}
    reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
                       'x1': 4.6, 'y1': 1, 'line': {'width': 8, 'color': 'black'}, 'layer': 'below'}
    box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    layout_['shapes'] = [reference_line_, box1_, box2_]
    layout_['legend'] = legend_layout_
    fig = go.Figure(layout=layout_)
    for algo in algos:
        if algo == overalgo:
            continue
        opacity_ = 1
        for t in nthreads:
            x_ = speedup[algo][t]['x']
            y_ = speedup[algo][t]['y']
            color_ = update_opacity(plotconfig[algo]['color'], opacity_)
            marker_ = {'color': color_, 'line': {
                'width': 1.5, 'color': 'black'}}
            fig.add_bar(x=x_, y=y_, marker=marker_,
                        name=algo + ' (n=' + str(t) + ')', showlegend=legend)
            opacity_ -= 1.0 / (len(u_rates) + 1)
    fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
    # fig.show()


def plot_exp2(dirpath, ds, max_key, include_unsafe=True):
    # Experiment 2 demonstrates performance as the workload distribution changes, with primitive operations 1:1 for contains and updates.

    # Create the required .csv files if there are none, then plot the data structure.
    csvfile = ds + '.csv'
    if not os.path.exists(os.path.join(dirpath, csvfile)):
        print('GENERATING .csv FILE FOR ' + ds + '...')
        subprocess.call('./make_csv.sh ' + dirpath + ' ' +
                        str(ntrials) + ' ' + ds, shell=True)

    print('GENERATING PLOT FOR ' + ds + '...')
    csv = CSVFile(os.path.join(dirpath, csvfile))
    x_axis = 'wrk_threads'
    y_axis = 'rq_latency'
    u_rates = [0, 5, 25, 45, 50]
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    for algo in plotconfig.keys():
        if algo == 'unsafe' and not include_unsafe:
            continue

        data[algo] = {}
        for u in u_rates:
            data[algo][u] = csv.getdata(x_axis, y_axis, [
                'list', 'max_key', 'u_rate'], [ds + '-' + algo, max_key, u])

    # Plot results.
    layout_ = {}
    fig = go.Figure(layout=layout_)
    for algo in plotconfig.keys():
        if algo == 'unsafe' and not include_unsafe:
            continue
        symbol_ = plotconfig[algo]['symbol']
        line_ = {'color': plotconfig[algo]['color']}
        opacity_ = 1
        for u in u_rates:
            x_ = data[algo][u]['x']
            y_ = data[algo][u]['y']
            marker_ = {"symbol": symbol_,
                       "opacity": opacity_, "size": 16}
            fig.add_trace(go.Scatter(
                x=x_, y=y_, name=algo + ' (' + str(u) + '% updates)', mode='markers+lines', marker=marker_, line=line_))
            # Update opacity to distiguish range query lengths.
            opacity_ -= 1.0 / (len(u_rates) + 1)

    fig.show()


def plot_memreclamation(dirpath, nofreedir, freedir, ds, max_key):
    # 'freedir' contains directories each with a different delay configuration.
    # Create the required .csv files if there are none, then plot the data structure.
    x_axis = 'wrk_threads'
    y_axis = 'tot_thruput'
    u_rates = [0, 10, 50, 90, 100]
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    for d in delayconfig.keys():
        if d != 'nofree':
            csvdir = os.path.join(dirpath, freedir, d, 'exp1')
            csvfile = os.path.join(csvdir, ds + '.csv')
        else:
            csvdir = os.path.join(dirpath, nofreedir, 'exp1')
            csvfile = os.path.join(csvdir, ds + '.csv')
        temp = os.path.join(dirpath, csvfile)
        if not os.path.exists(temp):
            print('GENERATING .csv FILE FOR ' + ds + '...')
            subprocess.call('./make_csv.sh ' + csvdir + ' ' +
                            str(ntrials) + ' ' + ds, shell=True)

        csv = CSVFile(os.path.join(dirpath, csvfile))
        x_axis = 'wrk_threads'
        y_axis = 'tot_thruput'
        u_rates = [0, 10, 50, 90, 100]
        # Accumulate the data for each algorithm and the corresponding
        data[d] = {}
        for u in u_rates:
                data[d][u] = csv.getdata(x_axis, y_axis, [
                    'list', 'max_key', 'u_rate'], [ds + '-lbundle', max_key, u])

    speedup = {}
    for d in data.keys():
        speedup[d] = {}
        for u in u_rates:
            speedup[d][u] = data['nofree'][u]['y'] / \
                data[d][u]['y']

    for d in speedup.keys():
      print(d)
      for u in u_rates:
        print(np.average(speedup[d][u]))


def plot_macrobench(dirpath, ds, ylabel=False, legend=False):
    csv = CSVFile(os.path.join(dirpath, 'data.csv'))
    data = {}
    for algo in plotconfig.keys():
        data[algo] = csv.getdata('nthreads', 'ixThroughput', [
                                 'rqalg', 'datastructure'], [plotconfig[algo]['macrobench'], ds])

    speedup = {}
    overalgo = 'unsafe'
    for algo in plotconfig.keys():
        if algo == overalgo:
            continue
        speedup[algo] = {}
        if data[algo]['y'].size == 0:
            speedup[algo]['x'] = []
            speedup[algo]['y'] = []
            continue
        speedup[algo]['x'] = data[overalgo]['x'][::2]
        try:
            speedup[algo]['y'] = data[algo]['y'][::2] / \
                data[overalgo]['y'][::2]
        except:
            shape_ = data[overalgo]['y'][::2].shape
            speedup[algo]['y'] = np.zeros(shape=shape_)

    x_axis_layout_['title']['text'] = '# Threads'
    x_axis_layout_['title']['font']['size'] = 58
    y_axis_layout_[
        'title']['text'] = 'Total Throughput (ops/s)' if ylabel else ''
    y_axis_layout_['title']['font']['size'] = 58
    legend_layout_ = {'font': legend_font_, 'orientation': 'h',
                      'x': 0, 'y': 1.3, 'font': {'size': 28}} if legend else {}
    layout_['legend'] = legend_layout_
    fig = go.Figure(layout=layout_)
    for algo in plotconfig.keys():
        symbol_ = plotconfig[algo]['symbol']
        line_ = {'color': plotconfig[algo]['color']}
        opacity_ = 1
        x_ = data[algo]['x']
        y_ = data[algo]['y']
        marker_ = {'symbol': symbol_,
                   'opacity': opacity_, 'size': 40, 'line_width': 2}
        fig.add_trace(go.Scatter(
            x=x_, y=y_, name=plotconfig[algo]['label'], mode='markers+lines', marker=marker_, line=line_, showlegend=legend))
        # Update opacity to distiguish range query lengths.
    fig.show()

    # Plot speedup.
    # reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
    #                    'x1': 4.6, 'y1': 1, 'line': {'width': 8}, 'layer': 'below'}
    # box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
    #          'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    # box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
    #          'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    # layout_ = {'xaxis': x_axis_layout_,
    #            'yaxis': y_axis_layout_, 'shapes': [reference_line_, box1_, box2_]}
    # fig = go.Figure(layout=layout_)
    # for algo in speedup.keys():
    #     x_ = [str(i) for i in speedup[algo]['x']]
    #     y_ = speedup[algo]['y']
    #     marker_ = {'color': plotconfig[algo]['color'], 'line': {
    #         'width': 1.5, 'color': 'black'}}
    #     fig.add_bar(x=x_, y=y_, marker=marker_,
    #                 name=algo)
    # fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
    # fig.show()


def plot_relaxation(dirpath, ds, max_key, ylabel=False, legend=False):
    data = {}
    x_axis = 'u_rate'
    y_axis = 'tot_thruput'
    nthreads = [96]
    for c in relaxconfig.keys():
        csvfile = os.path.join(c, 'exp1/'+ds+'.csv')
        if not os.path.exists(os.path.join(dirpath, csvfile)):
            print('GENERATING .csv FILE FOR ' + ds + '...')
            subprocess.call('./make_csv.sh ' + os.path.join(dirpath, c, 'exp1') + ' ' +
                            str(ntrials) + ' ' + ds, shell=True)
        csv = CSVFile(os.path.join(dirpath, csvfile))
        data[c] = {}
        for t in nthreads:
            if t == 0:
                continue
            data[c][t] = csv.getdata(x_axis, y_axis, ['list', 'max_key', 'wrk_threads'], [
                ds+('-lbundle' if c != 'ubundle' else '-ubundle'), max_key, t])

    speedup = {}
    overalgo = 'relax1'
    for c in relaxconfig.keys():
        if c == overalgo:
            continue
        speedup[c] = {}
        for t in nthreads:
            if t == 0:
                continue
            speedup[c][t] = {}
            if data[c][t]['y'].size == 0:
                speedup[c][t]['x'] = []
                speedup[c][t]['y'] = []
                continue
            speedup[c][t]['x'] = data[overalgo][t]['x']
            try:
                speedup[c][t]['y'] = data[c][t]['y'] / \
                    data[overalgo][t]['y']
            except:
                shape_ = data[overalgo][t]['y'].shape
                speedup[c][t]['y'] = np.zeros(shape=shape_)

    x_axis_layout_['title']['text'] = '% Updates'
    y_axis_layout_['title']['text'] = 'Relative Throughput' if ylabel else ''
    x_axis_layout_['title']['font']['size'] =54 
    x_axis_layout_['tickfont']['size'] =54 
    y_axis_layout_['title']['font']['size'] =54 
    y_axis_layout_['tickfont']['size'] =54 
    reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
                       'x1': 3.6, 'y1': 1, 'line': {'width': 8, 'color': 'black'}, 'layer': 'below'}
    box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    legend_layout_ = {'font': legend_font_,
                      'orientation': 'v', 'x': 0, 'y': 1.15} if legend else {}
    layout_['shapes'] = [reference_line_, box1_, box2_]
    layout_['legend'] = legend_layout_
    fig = go.Figure(layout=layout_)
    i = 0
    for algo in speedup.keys():
        opacity_ = 1 - (i / (len(speedup.keys()) + 1))
        for t in nthreads:
            # x_ = speedup[algo][t]['x']
            x_ = speedup[algo][t]['x'][1:]
            y_ = speedup[algo][t]['y'][1:]
            color_ = update_opacity(plotconfig['lbundle']['color'], opacity_)
            marker_ = {'line': {
                'width': 1.5, 'color': 'black'}, 'color': color_}
            name_ = relaxconfig[algo]['label'] + \
                (('(' + str(t) + ')') if len(nthreads) != 1 else '')
            fig.add_bar(x=x_, y=y_, marker=marker_,
                        name=name_, showlegend=legend)
        i += 1
    fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
    fig.show()


def plot_ubundle(dirpath, ds, max_key):
        # Experiment 1 demonstrates performance as the workload distribution changes.

    # Create the required .csv files if there are none, then plot the data structure.
    algos = ['lbundle', 'ubundle']
    csvfile = ds + '.csv'
    if not os.path.exists(os.path.join(os.path.join(dirpath, 'exp1'), csvfile)):
        print('GENERATING .csv FILE FOR ' + ds + '...')
        subprocess.call('./make_csv.sh ' + os.path.join(dirpath, 'exp1') + ' ' +
                        str(ntrials) + ' ' + ds, shell=True)

    print('GENERATING PLOT FOR ' + ds + '...')
    csv = CSVFile(os.path.join(os.path.join(dirpath, 'exp1'), csvfile))
    x_axis = 'u_rate'
    y_axis = 'tot_thruput'
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    nthreads = [1, 48, 96, 144, 192]
    for algo in algos:
        data[algo] = {}
        for t in nthreads:
            data[algo][t] = csv.getdata(x_axis, y_axis, [
                'list', 'max_key', 'wrk_threads'], [ds + '-' + algo, max_key, t])

    # Plot results.

    x_axis_layout_ = {'title': {'text': '# Threads',
                                'font': axis_font_}, 'tickfont': axis_font_}
    y_axis_layout_ = {'title': {
        'text': 'Total Throughput (ops/s)', 'font': axis_font_}, 'tickfont': axis_font_}
    legend_layout_ = {'font': legend_font_, 'orientation': 'h',
                      'x': 0, 'y': 1.1, 'font': {'size': 18}}
    layout_ = {'xaxis': x_axis_layout_,
               'yaxis': y_axis_layout_, 'legend': legend_layout_}
    fig = go.Figure(layout=layout_)
    # for algo in plotconfig.keys():
    #     if algo == 'unsafe' and not unsafe:
    #         continue
    #     symbol_ = plotconfig[algo]['symbol']
    #     line_ = {'color': plotconfig[algo]['color']}
    #     opacity_ = 1
    #     for u in u_rates:
    #         x_ = data[algo][u]['x']
    #         y_ = data[algo][u]['y']
    #         marker_ = {"symbol": symbol_,
    #                    "opacity": opacity_, "size": 40, 'line_width': 2}
    #         fig.add_trace(go.Scatter(
    #             x=x_, y=y_, name=algo + ' (' + str(u) + '% updates)', mode='markers+lines', marker=marker_, line=line_))
    #         # Update opacity to distiguish range query lengths.
    #         opacity_ -= 1.0 / (len(u_rates) + 1)

    # Calculate speedup.
    speedup = {}
    overalgo = 'lbundle'
    for algo in algos:
        if algo == overalgo:
            continue
        speedup[algo] = {}
        for t in nthreads:
            speedup[algo][t] = {}
            if data[algo][t]['y'].size == 0:
                speedup[algo][t]['x'] = []
                speedup[algo][t]['y'] = []
                continue
            speedup[algo][t]['x'] = data[overalgo][t]['x']
            try:
                speedup[algo][t]['y'] = data[algo][t]['y'] / \
                    data[overalgo][t]['y']
            except:
                shape_ = data[overalgo][t]['y'].shape
                speedup[algo][t]['y'] = np.zeros(shape=shape_)
            # speedup[algo][rq_size]['y'] =  data['lbundle'][rq_size]['y'][::2] / data[algo][rq_size]['y'][::2]

    # Plot speedup.
    x_axis_layout_ = {'type': 'category', 'title': {
        'text': '% Updates', 'font': axis_font_}, 'tickfont': axis_font_}
    y_axis_layout_ = {'title': {'text': '',
                                'font': axis_font_}, 'tickfont': axis_font_}
    reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
                       'x1': 4.6, 'y1': 1, 'line': {'width': 8}, 'layer': 'below'}
    box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    layout_ = {'xaxis': x_axis_layout_,
               'yaxis': y_axis_layout_, 'shapes': [reference_line_, box1_, box2_]}
    fig = go.Figure(layout=layout_)
    i = 0
    for t in nthreads:
        opacity_ = 1 - (float(i) / (len(u_rates) + 1))
        for algo in speedup.keys():
            # x_ = speedup[algo][u]['x']
            x_ = speedup[algo][t]['x']
            y_ = speedup[algo][t]['y']
            marker_ = {'color': update_opacity(relaxconfig[algo]['color'], opacity_), 'line': {
                'width': 1.5, 'color': 'black'}}
            name_ = 'T=' + str(t)
            fig.add_bar(x=x_, y=y_, marker=marker_,
                        name=name_)
        i += 1
    fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
    fig.show()


if __name__ == "__main__":
            # Experiment 0 features an even distribution of updates and range queries, with varied RQ lengths.
    rootdir = os.path.join(rootdir, machine)
    dirpath = os.path.join(rootdir, 'microbench/nofree')

    # EXPERIMENT 0.
    # plot_exp0(dirpath, 'lazylist', 10000, legend=True)
    # plot_exp0(dirpath, 'skiplistlock', 100000)
    # plot_exp0(dirpath, 'citrus', 100000)

    # EXPERIMENT 1.
    plot_exp1(dirpath, 'lazylist', 10000, True)
    plot_exp1(dirpath, 'skiplistlock', 100000)
    plot_exp1(dirpath, 'citrus', 100000)

    # OTHERS
    # plot_memreclamation(os.path.join(rootdir, 'microbench'),
    #                     'nofree', 'free', 'lazylist', 10000)
    # plot_macrobench(os.path.join(
    #     rootdir, 'macrobench', 'rq100'), 'SKIPLISTLOCK', ylabel=True, legend=True)
    plot_macrobench(os.path.join(rootdir, 'macrobench', 'rq100'), 'CITRUS', ylabel=True, legend=True)
    # rootdir, machine), 'macrobench'), 'CITRUS')
    # plot_relaxation(os.path.join(dirpath, 'exp3'), 'skiplistlock', 100000, ylabel=True, legend=True)
    # plot_ubundle(dirpath, 'skiplistlock', 100000)
