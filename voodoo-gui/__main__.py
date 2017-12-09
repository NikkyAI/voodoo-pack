#!/bin/python3
# -*- coding: utf-8 -*-

import signal

from pycallgraph import Config, GlobbingFilter, PyCallGraph
from pycallgraph.output import GraphvizOutput

from .app import main

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

if __name__ == "__main__":
    graphviz = GraphvizOutput(output_file='voodop-gui.png')
    config = Config()
    config.trace_filter = GlobbingFilter(exclude=[
        'pycallgraph.*',
        '*.secret_function',
    ])

    with PyCallGraph(output=graphviz, config=config):
        main()
