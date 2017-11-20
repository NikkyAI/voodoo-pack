from pathlib import Path
from typing import List

from graphviz import Digraph

from .cftypes import DependencyType, Side

def generate_graph(entries: List[dict], path: Path):
    color_map = {
        Side.Client: 'lawngreen',
        Side.Server: 'deepskyblue',
        Side.Both: 'grey'
    }
    dot = Digraph(comment='Dependencies', filename=path / 'dependencies', format='png', engine='dot') # 'sdfp'
    
    with dot.subgraph(name='cluster_legend') as legend:
        legend.attr(style='filled,dashed')
        legend.attr(color='lightgrey')
        legend.attr(label='legend')
        for side, color in color_map.items():
            legend.node(str(side), color=color, style='filled', contraint='true')
    
    for entry in entries:
        name = entry.get('name', entry.get('file_name')) or 'unnamed'
        side = Side.get(entry.get('side', 'both'))
        dot.node(name, name, style='filled', color=color_map[side])

    # TODO: subgraphs for features

    for entry in entries:
        name = entry.get('name', entry.get('file_name'))
        depends = entry.get('depends', {})
        for dep_type, dep_list in depends.items():
            for dependency in dep_list:
                dep_type = DependencyType.get(dep_type)
                if not any(e.get('name') == dependency for e in entries):
                    dot.node(dependency, dependency, style='filled', color='dimgray')
                    #continue #TODO: add option to skip

                style = 'dashed' if dep_type == DependencyType.Optional else 'solid'
                dot.edge(name, dependency, label=str(dep_type), style=style)
    
    dot.attr(label=r'\n\nTODO: pack name here')
    dot.attr(fontsize='20')
    dot.render()
