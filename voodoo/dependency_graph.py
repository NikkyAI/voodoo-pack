from pathlib import Path
from typing import List

from graphviz import Digraph

from .cftypes import DependencyType

def generate_graph(entries: List[dict], path: Path):
    dot = Digraph(comment='Dependencies', filename=path / 'dependencies', format='png', engine='sfdp')
    for entry in entries:
        name = entry.get('name', entry.get('file_name')) or 'unnamed'
        dot.node(name, name)

    # TODO: subgraphs for features

    for entry in entries:
        name = entry.get('name', entry.get('file_name'))
        depends = entry.get('depends', {})
        for dep_type, dep_list in depends.items():
            for dependency in dep_list:
                dep_type = DependencyType.get(dep_type)
                if not any(e.get('name') == dependency for e in entries):
                    dot.node(dependency, dependency, style='filled', color='darkslategrey')
                    # continue
                dot.edge(name, dependency, label=str(dep_type))

    dot.render()
