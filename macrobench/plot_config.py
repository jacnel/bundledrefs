# Configurations for plotting each experiment.
dirconfig = {
    'rootdir': 'macrobench/',
    'machine': '',
}

datastructures = {
    'skiplist': {'filename': 'skiplistlock_100.csv', 'list': 'SKIPLISTLOCK'},
    'citrus': {'filename': 'citrus_100.csv', 'list': 'CITRUS'},
}

plots = {
    'test': {'title': 'Title', 'datadir': '', 'x': 'nthreads', 'y': ['ixThroughput'], 'filter_on': []},
}

algs = {
    'RQ_LOCKFREE': {'color': 'royalblue'},
    'RQ_RWLOCK': {'color': 'firebrick'},
    'RQ_BUNDLE': {'color': 'seagreen'},
}
