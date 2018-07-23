import pydot
import os
from pygears.core.hier_node import HierVisitorBase
from pygears.util.find import find
from pygears import registry
from pygears.util import print_hier


class Visitor(HierVisitorBase):
    def __init__(self):
        self.gear_map = {}
        self.node_map = {}
        self.graph = pydot.Dot(
            graph_type='digraph', rankdir='LR', overlap=False)
        self.hier = [self.graph]
        self.sim_map = registry('SimMap')
        self.outdir = registry('SimArtifactDir')

    def enter_hier(self, module):
        self.hier.append(self.gear_map[module])

    def exit_hier(self, module):
        node = self.hier.pop()
        self.hier[-1].add_subgraph(node)

    def Gear(self, module):
        gear_fn = module.name.replace('/', '_')
        gear_stem = os.path.abspath(
            os.path.join(self.outdir, gear_fn))

        v = print_hier.Visitor(params=True, fullname=True)
        v.visit(module)
        with open(f'{gear_stem}.txt', 'w') as f:
            f.write('\n'.join(v.res))

        if module in self.sim_map:
            self.gear_map[module] = pydot.Node(
                module.name,
                tooltip=module.name,
                label=module.basename,
                URL=f"localhost:5000/{gear_fn}")

            self.node_map[module] = self.gear_map[module]
            self.hier[-1].add_node(self.gear_map[module])
        else:
            self.gear_map[module] = pydot.Cluster(
                graph_name=module.name,
                label=module.basename,
                tooltip=module.name,
                fontsize=48,
                fontcolor='blue',
                labeljust='l',
                overlap=False,
                # URL=f"file://{desc_fn}")
                URL=f"localhost:5000/{gear_fn}")

            self.enter_hier(module)

            super().HierNode(module)

            self.exit_hier(module)

        return True


def graph(path='/', root=None):
    top = find(path, root)
    v = Visitor()
    v.visit(top)

    v.edge_map = {}

    for module, node in v.node_map.items():
        for pout in module.out_ports:
            edges = pout.producer.end_consumers

            for e in edges:
                v.edge_map[e] = pydot.Edge(
                    node,
                    v.node_map[e.gear],
                    label=f"{pout.basename} -> {e.basename}")
                v.graph.add_edge(v.edge_map[e])

    return v