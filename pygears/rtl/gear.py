from pygears.rtl.node import RTLNode
from pygears.rtl.intf import RTLIntf
from pygears.core.port import InPort
import itertools
from pygears import registry
from pygears.core.hier_node import HierNode
from pygears import registry, PluginBase
from pygears.core.hier_node import HierVisitorBase
import inspect


def reconnect_port(gear_port, port):
    iin = gear_port.producer
    iout = gear_port.consumer

    if iin:
        # iin.disconnect(gear_port)
        iin.connect(port)

    if iout:
        # iout.disconnect(gear_port)
        iout.source(port)


class RTLGear(RTLNode):
    def __init__(self, gear, parent):
        super().__init__(parent, gear.basename, params=gear.params)
        self.gear = gear


def is_gear_instance(node, definition):
    if isinstance(node, RTLGear):
        return node.gear.definition is definition

    return False


class RTLGearHierVisitor(HierVisitorBase):
    def RTLGear(self, node):
        gear = node.gear
        if hasattr(self, gear.definition.__name__):
            return getattr(self, gear.definition.__name__)(node)


class RTLGearNodeGen(HierNode):
    def __init__(self, gear, parent):
        super().__init__(parent)
        self.gear = gear
        self.node = RTLGear(gear, getattr(parent, "node", None))

        namespace = registry('SVGenModuleNamespace')

        if 'svgen' not in self.node.params:
            self.node.params['svgen'] = {}

        if 'svgen_cls' not in self.node.params['svgen']:
            svgen_cls = namespace.get(gear.definition, None)

            if svgen_cls is None:
                for base_class in inspect.getmro(gear.__class__):
                    if base_class.__name__ in namespace:
                        svgen_cls = namespace[base_class.__name__]
                        break

            self.node.params['svgen']['svgen_cls'] = svgen_cls

        for p in gear.in_ports:
            self.node.add_in_port(p.basename, p.producer, p.consumer, p.dtype)

        for p in gear.out_ports:
            self.node.add_out_port(p.basename, p.producer, p.consumer, p.dtype)

        # for gear_port, port in zip(
        #         itertools.chain(gear.in_ports, gear.out_ports),
        #         itertools.chain(self.node.in_ports, self.node.out_ports)):
        #     reconnect_port(gear_port, port)

    def connect(self):
        self.rtl_map = registry('RTLNodeMap')
        for p, gear_p in zip(self.node.in_ports, self.gear.in_ports):
            self.create_intf(p, gear_p, domain=self.node)
            # prod_intf = p.producer
            # if prod_intf is not None and prod_intf.producer is None:
            #     self.create_unsourced_intf(p)

        for p, gear_p in zip(self.node.out_ports, self.gear.out_ports):
            self.create_intf(p, gear_p, domain=self.node.parent)

    # def create_unsourced_intf(self, port):
    #     intf = port.producer
    #     consumers = []
    #     for cons_port in intf.consumers:
    #         rtl_port = cons_port.node.in_ports[cons_port.index]
    #         consumers.append(rtl_port)

    #     intf_inst = RTLIntf(
    #         self.node.root(), intf.dtype, producer=None, consumers=consumers)

    #     for cons_port in consumers:
    #         cons_port.producer = intf_inst

    #     self.rtl_map[intf] = intf_inst
    #     port.producer = intf_inst

    def create_intf(self, port, gear_port, domain):
        gear_intf = gear_port.consumer
        if gear_intf is not None:
            consumers = []
            for cons_port in gear_intf.consumers:
                node_gen = registry('RTLNodeMap').get(cons_port.gear, None)
                if node_gen:
                    node = node_gen.node

                    if isinstance(cons_port, InPort):
                        port_group = node.in_ports
                    else:
                        port_group = node.out_ports

                    rtl_port = port_group[cons_port.index]
                    consumers.append(rtl_port)

            intf_inst = RTLIntf(
                domain, gear_intf.dtype, producer=port, consumers=consumers)

            for cons_port in consumers:
                cons_port.producer = intf_inst

            self.rtl_map[gear_intf] = intf_inst
            port.consumer = intf_inst


class RTLInstPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['RTLModuleNamespace'] = {}
        cls.registry['RTLClsMap'] = {}
