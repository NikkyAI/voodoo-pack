from graphviz import Digraph
from typing import List
from pathlib import Path
import tempfile

def generate_graph(entries: List[dict], path: Path):
    dot = Digraph(comment='Dependencies', filename=path / 'dependencies', format='png', engine='sfdp')
    for entry in entries:
        name = entry.get('name', entry.get('file_name'))
        dot.node(name, name)

    # TODO: subgraphs for features

    for entry in entries:
        name = entry.get('name', entry.get('file_name'))
        depends = entry.get('depends', {})
        for dep_type, dep_list in depends.items():
            for dependency in dep_list:
                dot.edge(name, dependency, label=dep_type)

    # dot.render(view=True)
    dot.render()