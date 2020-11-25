import numpy as np
import plotly
import plotly.graph_objects as go
from plotly import subplots
from plot_util import *
import argparse

## The following is necessary to get plotly's export feature to play nicely with Anaconda.
plotly.io.orca.config.executable = '/usr/local/anaconda3/envs/bundledrefs/bin/orca'


def plot_workload(dirpath, ds, max_key, u_rate, rq_rate, ylabel=False, legend=False, save=False):
    """ Generates a plot showing throughput as a function of number of threads
        for the given data structure. """
    reset_base_config()
    csvfile = CSVFile.get_or_gen_csv(
        os.path.join(dirpath, 'workloads'), ds, ntrials)
    csv = CSVFile(csvfile)

    ## Provide column labels for desired x and y axis
    x_axis = 'wrk_threads'
    y_axis = 'tot_thruput'

    ## Init data store
    data = {}

    ## Ignores rows in .csv with the following label
    ignore = ['ubundle']
    algos = [k for k in plotconfig.keys() if k not in ignore]

    ## Read in data for each algorithm
    for a in algos:
        data[a] = {}
        data[a] = csv.getdata(x_axis, y_axis, ['list', 'max_key', 'u_rate', 'rq_rate'], [
                              ds+'-'+a, max_key, u_rate, rq_rate])
        data[a]['y'] = data[a]['y'] / 1000000  # Normalize data

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
        filename = ds + '_u' + str(u_rate) + '_rq' + str(rq_rate)
        fig.write_image('./figures/'+filename+'.pdf')

    # Print speedup for paper.
    ignore = ['ubundle']
    testalgo = 'unsafe'
    overalgos = [k for k in plotconfig.keys() if (
        k not in ignore and k != testalgo)]
    print('Speedup for ' + ds + ' @ ' + str(u_rate) + '% updates')
    for o in overalgos:
        try:
            print(testalgo + ' / ' + o + '\n\t' +
                  str(data[testalgo]['y'][0::2] / data[o]['y'][0::2]))
        except ValueError:
            print(testalgo + ' / ' + o + ' []')


def plot_rq_sizes(dirpath, dss, max_key, ylabel=False, legend=False, save=False):
    # Experiment 1 demonstrates performance as the workload distribution changes.

    # Create the required .csv files if there are none, then plot the data structure.ß

    reset_base_config()
    x_axis = 'rq_size'
    y_axis = 'tot_thruput'
    nthreads = [24, 48, 96, 144, 192]
    # Accumulate the data for each algorithm and the corresponding
    data = {}
    ignore = ['ubundle']
    algos = [k for k in plotconfig.keys() if k not in ignore]
    for ds in dss:
        csvfile = CSVFile.get_or_gen_csv(
            os.path.join(dirpath, 'exp0'), ds, ntrials)
        csv = CSVFile(csvfile)
        data[ds] = {}
        for algo in algos:
            data[ds][algo] = {}
            for t in nthreads:
                data[ds][algo][t] = csv.getdata(x_axis, y_axis, [
                    'list', 'max_key', 'wrk_threads'], [ds + '-' + algo, max_key, t])
                print(algo + '=' + str(data[ds][algo][t]['y']))

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
                      'orientation': 'v', 'x': 0, 'y': 1.15, 'traceorder': 'grouped', 'tracegroupgap': 0} if legend else {}

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

    # fig = go.Figure(layout=layout_)
    fig = plotly.subplots.make_subplots(
        rows=len(dss), cols=2, column_widths=[0.03, 0.97],
        specs=[[{'rowspan': 2}, {}],
               [None, {}]], shared_xaxes=True)
    curr_row_ = 1
    legend_shown_ = not legend  # If not legend then no legend is shown.
    for ds in dss:
        showlegend_ = not legend_shown_ and ds != 'skiplistlock'
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
                            ' (n=' + str(t) + ')</b>',
                            legendgroup=ds, showlegend=showlegend_,
                            row=curr_row_, col=2)
                opacity_ -= 1.0 / (len(nthreads) + 1)
        curr_row_ += 1
        if showlegend_:
            legend_shown_ = True

    fig.update_xaxes(x_axis_layout_)
    fig.update_xaxes(title_text='Range Query Size', row=2, col=2)

    fig.update_yaxes(y_axis_layout_)
    fig.update_yaxes(title_text='Skip list', row=1, col=2)
    fig.update_yaxes(title_text='Citrus tree', row=2, col=2)

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
        fig.write_image('./figures/rqsize.pdf')


def plot_macrobench(dirpath, ds, ylabel=False, legend=False, save=False):
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

        ## Uncommenting below and commenting above will include fewer points on the plot
        # fig.add_trace(go.Scatter(
        #     x=x_[0::2], y=y_[0::2], name=name_, mode='markers+lines', marker=marker_, line=line_, showlegend=legend))

    if not save:
        fig.show()
    else:
        fig.write_image('./figures/'+ds+'-macrobench.pdf')


# def plot_relaxation(dirpath, ds, max_key, ylabel=False, legend=False):
#     reset_base_config()
#     data = {}
#     x_axis = 'u_rate'
#     y_axis = 'tot_thruput'
#     nthreads = [96]
#     for c in relaxconfig.keys():
#         # TODO: Update to use new utils.
#         csvfile = os.path.join(c, 'exp1/'+ds+'.csv')
#         if not os.path.exists(os.path.join(dirpath, csvfile)):
#             print('GENERATING .csv FILE FOR ' + ds + '...')
#             subprocess.call('./make_csv.sh ' + os.path.join(dirpath, c, 'exp1') + ' ' +
#                             str(ntrials) + ' ' + ds, shell=True)
#         csv = CSVFile(os.path.join(dirpath, csvfile))
#         data[c] = {}
#         for t in nthreads:
#             if t == 0:
#                 continue
#             data[c][t] = csv.getdata(x_axis, y_axis, ['list', 'max_key', 'wrk_threads'], [
#                 ds+('-lbundle' if c != 'ubundle' else '-ubundle'), max_key, t])

#     speedup = {}
#     overalgo = 'relax1'
#     for c in relaxconfig.keys():
#         if c == overalgo:
#             continue
#         speedup[c] = {}
#         for t in nthreads:
#             if t == 0:
#                 continue
#             speedup[c][t] = {}
#             if data[c][t]['y'].size == 0:
#                 speedup[c][t]['x'] = []
#                 speedup[c][t]['y'] = []
#                 continue
#             speedup[c][t]['x'] = data[overalgo][t]['x']
#             try:
#                 speedup[c][t]['y'] = data[c][t]['y'] / \
#                     data[overalgo][t]['y']
#             except:
#                 shape_ = data[overalgo][t]['y'].shape
#                 speedup[c][t]['y'] = np.zeros(shape=shape_)

#     x_axis_layout_['title']['text'] = '% Updates'
#     y_axis_layout_['title']['text'] = 'Rel. Throughput' if ylabel else ''
#     x_axis_layout_['title']['font']['size'] = 50
#     x_axis_layout_['tickfont']['size'] = 50
#     y_axis_layout_['title']['font']['size'] = 50
#     y_axis_layout_['tickfont']['size'] = 50
#     y_axis_layout_['nticks'] = 4
#     reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
#                        'x1': 3.6, 'y1': 1, 'line': {'width': 8, 'color': 'black'}, 'layer': 'below'}
#     box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
#              'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
#     box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
#              'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
#     legend_layout_ = {'font': legend_font_,
#                       'orientation': 'h', 'x': 0, 'y': 1.15} if legend else {}
#     # legend_layout_['font']['size'] = 50
#     layout_['shapes'] = [reference_line_, box1_, box2_]
#     layout_['legend'] = legend_layout_
#     layout_['width'] = 1400
#     layout_['height'] = 550

#     fig = go.Figure(layout=layout_)
#     i = 0
#     for algo in speedup.keys():
#         opacity_ = 1 - (i / (len(speedup.keys()) + 1))
#         for t in nthreads:
#             # x_ = speedup[algo][t]['x']
#             x_ = speedup[algo][t]['x'][1:]
#             y_ = speedup[algo][t]['y'][1:]
#             color_ = update_opacity(plotconfig['lbundle']['color'], opacity_)
#             marker_ = {'line': {
#                 'width': 1.5, 'color': 'black'}, 'color': color_}
#             name_ = relaxconfig[algo]['label'] + \
#                 (('(' + str(t) + ')') if len(nthreads) != 1 else '')
#             fig.add_bar(x=x_, y=y_, marker=marker_,
#                         name=name_, showlegend=legend)
#         i += 1
#     fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
#     fig.write_image('./figures/'+ds+'relax.pdf')
#     # fig.show()


# def plot_ubundle(dirpath, ds, max_key):
#     # Experiment 1 demonstrates performance as the workload distribution changes.

#     # Create the required .csv files if there are none, then plot the data structure.
#     reset_base_config()
#     algos = ['lbundle', 'ubundle']
#     csvfile = ds + '.csv'
#     if not os.path.exists(os.path.join(os.path.join(dirpath, 'exp1'), csvfile)):
#         print('GENERATING .csv FILE FOR ' + ds + '...')
#         subprocess.call('./make_csv.sh ' + os.path.join(dirpath, 'exp1') + ' ' +
#                         str(ntrials) + ' ' + ds, shell=True)

#     print('GENERATING PLOT FOR ' + ds + '...')
#     csv = CSVFile(os.path.join(os.path.join(dirpath, 'exp1'), csvfile))
#     x_axis = 'u_rate'
#     y_axis = 'tot_thruput'
#     # Accumulate the data for each algorithm and the corresponding
#     data = {}
#     nthreads = [1, 48, 96, 144, 192]
#     for algo in algos:
#         data[algo] = {}
#         for t in nthreads:
#             data[algo][t] = csv.getdata(x_axis, y_axis, [
#                 'list', 'max_key', 'wrk_threads'], [ds + '-' + algo, max_key, t])

#     # Plot results.

#     x_axis_layout_ = {'title': {'text': '# Threads',
#                                 'font': axis_font_}, 'tickfont': axis_font_}
#     y_axis_layout_ = {'title': {
#         'text': 'Total Throughput (ops/s)', 'font': axis_font_}, 'tickfont': axis_font_}
#     legend_layout_ = {'font': legend_font_, 'orientation': 'h',
#                       'x': 0, 'y': 1.1, 'font': {'size': 18}}
#     layout_ = {'xaxis': x_axis_layout_,
#                'yaxis': y_axis_layout_, 'legend': legend_layout_}
#     fig = go.Figure(layout=layout_)
#     # for algo in plotconfig.keys():
#     #     if algo == 'unsafe' and not unsafe:
#     #         continue
#     #     symbol_ = plotconfig[algo]['symbol']
#     #     line_ = {'color': plotconfig[algo]['color']}
#     #     opacity_ = 1
#     #     for u in u_rates:
#     #         x_ = data[algo][u]['x']
#     #         y_ = data[algo][u]['y']
#     #         marker_ = {"symbol": symbol_,
#     #                    "opacity": opacity_, "size": 40, 'line_width': 2}
#     #         fig.add_trace(go.Scatter(
#     #             x=x_, y=y_, name=algo + ' (' + str(u) + '% updates)', mode='markers+lines', marker=marker_, line=line_))
#     #         # Update opacity to distiguish range query lengths.
#     #         opacity_ -= 1.0 / (len(u_rates) + 1)

#     # Calculate speedup.
#     speedup = {}
#     overalgo = 'lbundle'
#     for algo in algos:
#         if algo == overalgo:
#             continue
#         speedup[algo] = {}
#         for t in nthreads:
#             speedup[algo][t] = {}
#             if data[algo][t]['y'].size == 0:
#                 speedup[algo][t]['x'] = []
#                 speedup[algo][t]['y'] = []
#                 continue
#             speedup[algo][t]['x'] = data[overalgo][t]['x']
#             try:
#                 speedup[algo][t]['y'] = data[algo][t]['y'] / \
#                     data[overalgo][t]['y']
#             except:
#                 shape_ = data[overalgo][t]['y'].shape
#                 speedup[algo][t]['y'] = np.zeros(shape=shape_)
#             # speedup[algo][rq_size]['y'] =  data['lbundle'][rq_size]['y'][::2] / data[algo][rq_size]['y'][::2]

#     # Plot speedup.
#     x_axis_layout_ = {'type': 'category', 'title': {
#         'text': '% Updates', 'font': axis_font_}, 'tickfont': axis_font_}
#     y_axis_layout_ = {'title': {'text': '',
#                                 'font': axis_font_}, 'tickfont': axis_font_}
#     reference_line_ = {'type': 'line', 'x0': -.6, 'y0': 1,
#                        'x1': 4.6, 'y1': 1, 'line': {'width': 8}, 'layer': 'below'}
#     box1_ = {'type': 'rect', 'yref': 'paper', 'x0': .5, 'x1': 1.5, 'y0': 0, 'y1': 1,
#              'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
#     box2_ = {'type': 'rect', 'yref': 'paper', 'x0': 2.5, 'x1': 3.5, 'y0': 0, 'y1': 1,
#              'layer': 'below', 'line': {'width': 0}, 'fillcolor': 'slategray', 'opacity': 0.25}
#     layout_ = {'xaxis': x_axis_layout_,
#                'yaxis': y_axis_layout_, 'shapes': [reference_line_, box1_, box2_]}
#     fig = go.Figure(layout=layout_)
#     i = 0
#     for t in nthreads:
#         opacity_ = 1 - (float(i) / (len(nthreads) + 1))
#         for algo in speedup.keys():
#             # x_ = speedup[algo][u]['x']
#             x_ = speedup[algo][t]['x']
#             y_ = speedup[algo][t]['y']
#             marker_ = {'color': update_opacity(relaxconfig[algo]['color'], opacity_), 'line': {
#                 'width': 1.5, 'color': 'black'}}
#             name_ = 'T=' + str(t)
#             fig.add_bar(x=x_, y=y_, marker=marker_,
#                         name=name_)
#         i += 1
#     fig.update_layout(barmode='group', bargap=0.05, bargroupgap=0.01)
#     fig.show()


# def plot_memreclamation(dirpath, nofreedir, freedir, ds, max_key):
#     # 'freedir' contains directories each with a different delay configuration.
#     # Create the required .csv files if there are none, then plot the data structure.
#     reset_base_config()
#     x_axis = 'wrk_threads'
#     y_axis = 'tot_thruput'
#     u_rates = [0, 10, 50, 90, 100]
#     # Accumulate the data for each algorithm and the corresponding
#     data = {}
#     for d in delayconfig.keys():
#         if d != 'nofree':
#             csvdir = os.path.join(dirpath, freedir, d, 'exp1')
#             csvfile = os.path.join(csvdir, ds + '.csv')
#         else:
#             csvdir = os.path.join(dirpath, nofreedir, 'exp1')
#             csvfile = os.path.join(csvdir, ds + '.csv')
#         temp = os.path.join(dirpath, csvfile)
#         if not os.path.exists(temp):
#             print('GENERATING .csv FILE FOR ' + ds + '...')
#             subprocess.call('./make_csv.sh ' + csvdir + ' ' +
#                             str(ntrials) + ' ' + ds, shell=True)

#         csv = CSVFile(temp)
#         x_axis = 'wrk_threads'
#         y_axis = 'tot_thruput'
#         u_rates = [0.0, 10.0, 50.0, 90.0, 100.0]
#         # Accumulate the data for each algorithm and the corresponding
#         data[d] = {}
#         for u in u_rates:
#             data[d][u] = csv.getdata(x_axis, y_axis, [
#                 'list', 'max_key', 'u_rate'], [ds + '-lbundle', max_key, u])

#     speedup = {}
#     for d in data.keys():
#         speedup[d] = {}
#         for u in u_rates:
#             speedup[d][u] = data['nofree'][u]['y'] / \
#                 data[d][u]['y']

#     for d in speedup.keys():
#         print(d)
#         for u in u_rates:
#             print(np.average(speedup[d][u]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--save_plots', action='store_true',
                        default=False, dest='save_plots')
    parser.add_argument('--microbench', action='store_true', default=True, dest='microbench')
    parser.add_argument('--macrobench', action='store_true', default=False, dest='macrobench')
    args = parser.parse_args()

    print(os.path.curdir)

    if not os.path.exists('./figures'):
        os.mkdir('./figures')

    ## Plot microbench results.
    if args.microbench:
        microbench_dir = 'microbench/data'

        # datastructures = ['lazylist', 'skiplistlock', 'citrus']
        datastructures = ['skiplistlock']
        max_keys_dict = {'lazylist': 10000,
                         'skiplistlock': 100000, 'citrus': 100000}
        rqrate = 10 
        urates = [0, 2, 10, 50, 90, 100]

        for ds in datastructures:
            for u in urates:
                plot_workload(
                    microbench_dir, ds, max_keys_dict[ds], u, rqrate, True, True, args.save_plots)
                pass

    ## Plot macrobench results.
    if args.macrobench:
        macrobench_dir = 'macrobench/data'
        plot_macrobench(os.path.join(macrobench_dir, 'rq_tpcc'),
                        'SKIPLISTLOCK', ylabel=True, legend=True, save=args.save_plots)
        plot_macrobench(os.path.join(macrobench_dir, 'rq_tpcc'),
                        'CITRUS', ylabel=True, legend=True, save=args.save_plots)
