from pathlib import Path
from typing import List

from graphviz import Digraph

from .cftypes import DependencyType, Side

def generate_graph(entries: List[dict], path: Path, pack_name: str):
    side_color = {
        Side.Client: 'lawngreen',
        Side.Server: 'deepskyblue',
        Side.Both: 'grey'
    }

    depedency_style = {
        DependencyType.Required: 'solid',
        DependencyType.Optional: 'dashed',
        DependencyType.Embedded: 'dotted'
    }

    recommendation_color = {
        'starred': 'green',
        'avoid': 'red',
    }
    selected_color = {
        True: 'cyan',
        False: 'darkslategray',
    }

    dot = Digraph(comment='Dependencies', filename=path / 'dependencies', format='png', engine='fdp') # 'sdfp'
    
    with dot.subgraph(name='cluster_legend') as legend:
        legend.attr(style='filled,dashed')
        legend.attr(fillcolor='lightgrey')
        legend.attr(label='legend')
        with legend.subgraph(name='cluster_sides') as side_cluster:
            side_cluster.attr(label='sides')
            for side, color in side_color.items():
                side_cluster.node(str(side), color=color, style='filled')
        with legend.subgraph(name='cluster_dependencies') as dependency_cluster:
            dependency_cluster.attr(label='dependencies')
            for dependency, style in depedency_style.items():
                dependency_cluster.node(str(dependency), str(dependency), style=style)
                dependency_cluster.edge('Dependency', str(dependency), style=style, len='2.0')
        with legend.subgraph(name='cluster_recommendation') as recommendation_cluster:
            recommendation_cluster.attr(label='recommendation')
            for recommendation, color in recommendation_color.items():
                recommendation_cluster.node('recommendation_'+recommendation, recommendation, style='filled,dashed', fillcolor=color)
        with legend.subgraph(name='cluster_selected') as selected_cluster:
            selected_cluster.attr(label='selected')
            for selected, color in selected_color.items():
                selected_cluster.node(f'selected_{selected}', str(selected), style='filled,solid', fillcolor=color)
        legend.attr(style='filled')


    for entry in entries:
        name = entry.get('name', entry.get('file_name')) or 'unnamed'
        side = Side.get(entry.get('side', 'both'))

        feature_name = entry.get('feature_name')
        if feature_name:
            recommendation = entry.get('recommendation') #, 'none'
            selected = entry.get('selected')
            with dot.subgraph(name=f'cluster_{feature_name}') as feature:
                feature.attr(style='striped')
                # feature.attr(fillcolor=recommendation_fillcolor[recommendation])
                fillcolor = f'lightgrey'
                if recommendation:
                    fillcolor += f':{recommendation_color[recommendation]};0.1'
                fillcolor += f':{selected_color[selected]};0.1'

                feature.attr(fillcolor=fillcolor)
                feature.attr(label=feature_name + '\n' + entry.get('description', ''))
                feature.node(name, color=side_color[side], style='filled')
                # if recommendation:
                #     feature.node(f'{feature_name}_{recommendation}', recommendation, style='filled,dashed', fillcolor=recommendation_color[recommendation])
        else:
            dot.node(name, name, style='filled', fillcolor=side_color[side])

    for entry in entries:
        name = entry.get('name', entry.get('file_name'))
        depends = entry.get('depends', {})
        for dep_type, dep_list in depends.items():
            for dependency in dep_list:
                dep_type = DependencyType.get(dep_type)
                if not any(e.get('name') == dependency for e in entries):
                    if dep_type == DependencyType.Embedded:
                        dot.node(dependency, dependency, style='dotted')
                    else:
                        dot.node(dependency, dependency, style='filled,dotted', fillcolor='dimgray')
                    # continue #TODO: add option to skip

                dot.edge(name, dependency, style=depedency_style[dep_type], len='3.0')

                

    dot.attr(label=f'\n\n{pack_name}')
    dot.attr(fontsize='20')
    dot.render()
