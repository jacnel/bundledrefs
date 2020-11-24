import numpy as np
import plotly
import plotly.graph_objects as go
from plotly import subplots
from plot_util import *
from plot_config import *
import argparse

# The following is necessary to get plotly's export feature to play nicely with Anaconda.
plotly.io.orca.config.executable = '/usr/local/anaconda3/envs/bundledrefs/bin/orca'


def plot_workload(dirpath, ds, max_key, u_rate, rq_rate, ylabel=False, legend=False, save=False, save_dir=""):
    """ Generates a plot showing throughput as a function of number of threads
        for the given data structure. """
    reset_base_config()
    csvfile = CSVFile.get_or_gen_csv(
        os.path.join(dirpath, 'workloads'), ds, ntrials)
    csv = CSVFile(csvfile)

    # Provide column labels for desired x and y axis
    x_axis = 'wrk_threads'
    y_axis = 'tot_thruput'

    # Init data store
    data = {}

    # Ignores rows in .csv with the following label
    ignore = ['ubundle']
    algos = [k for k in plotconfig.keys() if k not in ignore]

    # Read in data for each algorithm
    count = 0
    for a in algos:
        data[a] = {}
        data[a] = csv.getdata(x_axis, y_axis, ['list', 'max_key', 'u_rate', 'rq_rate'], [
                              ds+'-'+a, max_key, u_rate, rq_rate])
        count += len(data[a]['x'])
        data[a]['y'] = data[a]['y'] / 1000000  # Normalize data

    if count == 0:
        print('No data at given key range: ({}, {})'.format(ds, max_key))
        return  # If no data to ploy, then don't

    # Plot layout configuration.
    x_axis_layout_['title'] = None
    x_axis_layout_['tickfont']['size'] = 52
    x_axis_layout_['nticks'] = 6
    if ylabel:
        y_axis_layout_['title']['text'] = 'Mops/s'
        y_axis_layout_['title']['font']['size'] = 50
    else:
        y_axis_layout_['title'] = None
    y_axis_layout_['tickfont']['size'] = 52
    y_axis_layout_['nticks'] = 5
    legend_layout_ = {'font': legend_font_,
                      'orientation': 'h', 'x': 0, 'y': 1.15} if legend else {}
    layout_['legend'] = legend_layout_
    layout_['autosize'] = False
    layout_['width'] = 750
    layout_['height'] = 550

    fig = go.Figure(layout=layout_)
    for a in algos:
        symbol_ = plotconfig[a]['symbol']
        color_ = update_opacity(plotconfig[a]['color'], 1)
        marker_ = {'symbol': symbol_, 'color': color_, 'size': 40, 'line': {
            'width': 5, 'color': 'black'}}
        line_ = {'width': 10}
        name_ = '<b>' + plotconfig[a]['label'] + '</b>'
        fig.add_scatter(x=data[a]['x'], y=data[a]['y'], name=name_,
                        marker=marker_, line=line_, showlegend=legend)

        # Comment the above line and uncomment below to show fewer points per plot.
        # fig.add_scatter(x=data[a]['x'][0::2], y=data[a]['y'][0::2], name=name_,
        #                 marker=marker_, line=line_, showlegend=legend)

    if not save:
        fig.show()
    else:
        save_dir = os.path.join(save_dir, 'workloads/' + ds)
        os.makedirs(save_dir, exist_ok=True)
        filename = 'update' + str(u_rate) + '_rq' + \
            str(rq_rate) + '_maxkey' + str(max_key) + '.html'
        fig.write_html(os.path.join(save_dir, filename))

    # Print speedup for paper.
    ignore = ['ubundle']
    overalgo = 'unsafe'
    overalgos = [k for k in plotconfig.keys() if (
        k not in ignore and k != overalgo)]
    print('Speedup over "unsafe" for ' + ds +
          ' @ ' + str(u_rate) + '% updates\n')
    threads_printed = False
    for o in overalgos:
        if not threads_printed:
            print('{:<15}|'.format('algorithm'), end='')
            for i in range(len(data[o]['x']) // 2):
                print('{:10}'.format(''), end='')
            print('# threads')
            print('{:15}|'.format('---------------'), end='')
            for i in range(len(data[o]['x'])):
                print('{:10}'.format('----------'), end='')
            print()
            print('{:<15}|'.format(''), end='')
            for t in data[o]['x']:
                print('{:>10}'.format(t), end='')
            print()
            print('{:<15}|'.format(''), end='')
            for t in data[o]['x']:
                print('{:>10}'.format('-----'), end='')
            threads_printed = True

        if len(data[o]['x']) == 0:
            continue
        print('\n{:15}|'.format(''))
        print('{:<15}{}'.format(o, '|'), end='')
        for i in range(0, len(data[o]['x'])):
            print('{:>10.3}'.format(
                data[o]['y'][i] / data[overalgo]['y'][i]), end='')
    print('\n\n')


def plot_rq_sizes(dirpath, dss, max_key, nthreads, ylabel=False, legend=False, save=False, save_dir=""):
    # Experiment 1 demonstrates performance as the workload distribution changes.

    # Create the required .csv files if there are none, then plot the data structure.

    reset_base_config()
    x_axis = 'rq_size'
    y_axis = 'tot_thruput'
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    ignore = ['ubundle']
    algos = [k for k in plotconfig.keys() if k not in ignore]
    count = 0
    for ds in dss:
        csvfile = CSVFile.get_or_gen_csv(
            os.path.join(dirpath, 'rq_sizes'), ds, ntrials)
        csv = CSVFile(csvfile)
        data[ds] = {}
        for algo in algos:
            data[ds][algo] = {}
            for t in nthreads:
                data[ds][algo][t] = csv.getdata(x_axis, y_axis, [
                    'list', 'max_key', 'wrk_threads'], [ds + '-' + algo, max_key, t])
                count += len(data[ds][algo][t])
    
    if count == 0:
        print("No data found for rqsizes")
        return

    # Calculate speedup.
    speedup = {}
    overalgo = 'unsafe'
    for ds in dss:
        speedup[ds] = {}
        for algo in algos:
            if algo == overalgo:
                continue
            speedup[ds][algo] = {}
            for t in nthreads:
                speedup[ds][algo][t] = {}
                if data[ds][algo][t]['y'].size == 0:
                    speedup[ds][algo][t]['x'] = []
                    speedup[ds][algo][t]['y'] = []
                    continue
                speedup[ds][algo][t]['x'] = data[ds][overalgo][t]['x']
                try:
                    speedup[ds][algo][t]['y'] = data[ds][algo][t]['y'] / \
                        data[ds][overalgo][t]['y']
                except:
                    shape_ = data[ds][overalgo][t]['y'].shape
                    speedup[ds][algo][t]['y'] = np.zeros(shape=shape_)
                # speedup[algo][rq_size]['y'] =  data['lbundle'][rq_size]['y'][::2] / data[algo][rq_size]['y'][::2]

    # Plot speedup.
    x_axis_layout_['showgrid'] = False
    y_axis_layout_['dtick'] = .25

    legend_layout_ = {'font': legend_font_,
                      'orientation': 'v', 'x': 1.05, 'y': 0.5, 'traceorder': 'grouped', 'tracegroupgap': 0} if legend else {}

    reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
                       'x1': len(nthreads)+0.6, 'y1': 1, 'line': {'width': 8, 'color': 'black'}, 'layer': 'below'}

    box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
    box3_ = {'type': 'rect', 'yref': 'paper', 'x0': 4.5, 'x1': 5.5, 'y0': 0, 'y1': 1,
             'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}

    layout_['shapes'] = [box1_, box2_, box3_]
    layout_['legend'] = legend_layout_
    layout_['height'] = 750
    layout_['width'] = 2200


    specs2_ = [[{'rowspan': len(dss)}, {}],
              [None, {}]]
    specs3_ = [[{'rowspan': len(dss)}, {}],
               [None, {}],
               [None, {}]]
    specs_ = None
    if len(dss) == 2:
        specs_ = specs2_
    elif len(dss) == 3:
        specs_ = specs3_
    fig = plotly.subplots.make_subplots(
        rows=len(dss), cols=2, column_widths=[0.15, 0.85],
        specs=specs_, shared_xaxes=True)
    fig.update_xaxes(x_axis_layout_)
    fig.update_yaxes(y_axis_layout_)

    curr_row_ = 1
    for ds in dss:
        for algo in algos:
            if algo == overalgo:
                continue
            opacity_ = 1
            for t in nthreads:
                x_ = speedup[ds][algo][t]['x']
                y_ = speedup[ds][algo][t]['y']
                color_ = update_opacity(plotconfig[algo]['color'], opacity_)
                marker_ = {'color': color_, 'line': {
                    'width': 1.5, 'color': 'black'}}
                fig.add_bar(x=x_, y=y_, marker=marker_,
                            name='<b>' +
                            plotconfig[algo]['label'] +
                            ' (n=' + str(t) + ', ' + ds + ')</b>',
                            legendgroup=ds, showlegend=legend,
                            row=curr_row_, col=2)
                opacity_ -= 1.0 / (len(nthreads) + 1)
                fig.update_yaxes(title_text=str(ds), row=curr_row_, col=2)
        curr_row_ += 1

    fig.update_xaxes(title_text='Range Query Size', row=len(dss), col=2)

    annotations_ = [
        dict(
            x=0,
            y=0.5,
            showarrow=False,
            text="Rel. Throughput",
            textangle=-90,
            font=axis_font_,
            xref="paper",
            yref="paper"
        )
    ]
    fig.update_layout(layout_)
    fig.update_layout(barmode='group', bargap=0.05,
                      bargroupgap=0.01, annotations=annotations_)

    if not save:
        fig.show()
    else:
        filename = 'rqsize_maxkey' + str(max_key) + '.html'
        fig.write_html(os.path.join(save_dir, filename))


def plot_macrobench(dirpath, ds, ylabel=False, legend=False, save=False, save_dir=""):
    if not os.path.exists(os.path.join(dirpath, 'data.csv')):
        subprocess.call('./macrobench/make_csv.sh ' + os.path.join(dirpath,
                                                                   'summary.txt') + ' ' + os.path.join(dirpath, 'data.csv'), shell=True)

    reset_base_config()
    csv = CSVFile(os.path.join(dirpath, 'data.csv'))
    data = {}
    for algo in plotconfig.keys():
        data[algo] = csv.getdata('nthreads', 'ixThroughput', [
                                 'rqalg', 'datastructure'], [plotconfig[algo]['macrobench'], ds])
        data[algo]['y'] = data[algo]['y'] / 1000000  # Normalizes throughput.

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

    x_axis_layout_['title'] = None
    x_axis_layout_['tickfont']['size'] = 52
    y_axis_layout_['nticks'] = 6
    y_axis_layout_['tickfont']['size'] = 52
    if ylabel:
        y_axis_layout_['title']['text'] = 'Mops/s'
        y_axis_layout_['title']['font']['size'] = 50
    else:
        y_axis_layout_['title'] = None
    legend_layout_ = {'font': legend_font_, 'orientation': 'h',
                      'x': 0, 'y': 1.15} if legend else {}
    # legend_layout_['font']['size'] = 40
    layout_['legend'] = legend_layout_
    layout_['width'] = 750
    if legend:
        layout_['height'] = 750
    else:
        layout_['height'] = 350

    fig = go.Figure(layout=layout_)
    for algo in plotconfig.keys():
        symbol_ = plotconfig[algo]['symbol']
        line_ = {'width': 10, 'color': plotconfig[algo]['color']}
        opacity_ = 1
        x_ = data[algo]['x']
        y_ = data[algo]['y']
        marker_ = {'symbol': symbol_,
                   'opacity': opacity_, 'size': 40,
                   'line': {'color': 'black', 'width': 5 if not legend else 3}}
        name_ = '<b>' + plotconfig[algo]['label'] + '</b>'
        fig.add_trace(go.Scatter(
            x=x_, y=y_, name=name_, mode='markers+lines', marker=marker_, line=line_, showlegend=legend))

        # Uncommenting below and commenting above will include fewer points on the plot
        # fig.add_trace(go.Scatter(
        #     x=x_[0::2], y=y_[0::2], name=name_, mode='markers+lines', marker=marker_, line=line_, showlegend=legend))

    if not save:
        fig.show()
    else:
        filename = ds + '.html'
        fig.write_html(os.path.join(save_dir, filename))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--save_plots', action='store_true',
                        default=False, dest='save_plots')
    parser.add_argument('--microbench', action='store_true',
                        default=True, dest='microbench')
    parser.add_argument('--macrobench', action='store_true',
                        default=False, dest='macrobench')
    args = parser.parse_args()

    # Plot microbench results.
    if args.microbench:
        # Get configuration automatically
        config_config = parse_config('./config.mk')
        nthreads = [1]
        for i in range(config_config['threadincrement'], config_config['maxthreads'], config_config['threadincrement']):
            nthreads.append(i)
        nthreads.append(config_config['maxthreads'])
        print('Derived thread configuration from \"config.mk\": ' + str(nthreads))

        experiment_list_config = parse_experiment_list_generate(
            './microbench/experiment_list_generate.sh')
        print('Derived data structures and key ranges from \"./microbench/experiment_list_generate.sh\": ' + str(experiment_list_config))

        runscript_config = parse_runscript('./microbench/runscript.sh')
        print('Derived num trials from \"runscript.sh\":' + str(runscript_config))
        ntrials = runscript_config['trials']

        # Plot peformance at different workload configurations (corresponds to Figure 2)
        save_dir = './figures/microbench'
        for ds in experiment_list_config['datastructures']:
            for k in experiment_list_config['ksizes']:
                for u in workloads_urates:
                    if u == 100:
                        workloads_rqrate = 0
                    plot_workload(
                        microbench_dir, ds, k, u, workloads_rqrate, True, True, args.save_plots, save_dir)
                    pass

        # Plot performance w.r.t. range query size experiments at 50% updates and 50% range queries (corresponds to Figure 3)
        save_dir = './figures/microbench/rq_size'
        os.makedirs(save_dir, exist_ok=True)
        if rqsize_max_key not in experiment_list_config['ksizes']:
            print('Could not match key range to configuration derived from \"./microbench/experiment_list_generate.sh\"')
        plot_rq_sizes(microbench_dir, experiment_list_config['datastructures'],
                      rqsize_max_key, nthreads, True, True, args.save_plots, save_dir)

    # Plot macrobench results (corresponds to Figure 4)
    if args.macrobench:
        save_dir = './figures/macrobench/skiplistlock'
        os.makedirs(save_dir, exist_ok=True)
        plot_macrobench(os.path.join(macrobench_dir, 'rq_tpcc'),
                        'SKIPLISTLOCK', ylabel=True, legend=True, save=args.save_plots, save_dir=save_dir)
        save_dir = './figures/macrobench/citrus'
        os.makedirs(save_dir, exist_ok=True)
        plot_macrobench(os.path.join(macrobench_dir, 'rq_tpcc'),
                        'CITRUS', ylabel=True, legend=True, save=args.save_plots, save_dir=save_dir)