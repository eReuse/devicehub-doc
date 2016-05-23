"""
    Converts the API Schema to an UML Class Diagram.

    To use this module, install 'graphviz' through pip and just execute the class: Graphviz()
    You can add 2 parameters, the location of the file and the type.
"""
from ereuse_devicehub.resources.account.settings import Account
from ereuse_devicehub.resources.device.benchmark_settings import Benchmark
from ereuse_devicehub.resources.device.component.settings import Component
from ereuse_devicehub.resources.device.schema import Product
from ereuse_devicehub.resources.place.settings import Place
from graphviz import Digraph
from os.path import expanduser
from ereuse_devicehub.resources.event.settings import Event, EventWithOneDevice, EventWithDevices
from ereuse_devicehub.resources.schema import RDFS

from devicehub_doc.doc import Doc


class ClassDiagram(Doc):
    """
    Generates a class diagram for DeviceHub classes, using graphviz.

    the parameter `divide` of the initialization toggles the two ways of obtaining the diagram:
    - A big, full diagram.
    - Divided by different parts, so it is easily embeddable to documents.
    """
    def __init__(self, divide=True, img_format='pdf', file_prefix='devicehub diagram'):
        self.img_format = img_format
        self.directory = expanduser('~')
        self.file_prefix = file_prefix
        g = Digraph()
        options = {
            'nodesep': '0.2',
            'ranksep': '0.5',
            'margin': '0'
        }
        options_neato = dict(options, **{
            'overlap': 'ortho',
            'splines': 'true',
            'ranksep': '0.5',
            'nodesep': '0.5',
            'ratio': '2',
        })
        options_edge = {
            'len': '0.2'
        }
        classes = Digraph(graph_attr=options)
        products = Digraph(graph_attr=options)
        components = Digraph(engine='neato', graph_attr=options_neato, edge_attr=options_edge)
        events_with_one_device = Digraph(graph_attr=options)
        events_with_devices = Digraph(engine='neato', graph_attr=options_neato, edge_attr=options_edge)
        others = Digraph(graph_attr=options)
        if divide:
            for graph in (products, events_with_one_device, others, events_with_devices, components):
                self.initialize_graph(graph)
        else:
            self.initialize_graph(g)
        self.generate_class(RDFS, classes)
        product_subclasses = Product.subclasses() + [Product]
        event_with_one_device_subclasses = EventWithOneDevice.subclasses() + [Event, EventWithOneDevice]
        event_with_devices_subclasses = EventWithDevices.subclasses() + [Event, EventWithDevices]
        other_subclasses = Place.subclasses() + Benchmark.subclasses() + Account.subclasses() + [Place, Benchmark, Account]
        components_subclasses = Component.subclasses() + [Component]
        for subclass in RDFS.subclasses():
            if subclass in components_subclasses:
                self.generate_class(subclass, components)
            elif subclass in product_subclasses:
                self.generate_class(subclass, products)
            elif subclass in event_with_one_device_subclasses:
                self.generate_class(subclass, events_with_one_device)
            elif subclass in event_with_devices_subclasses:
                self.generate_class(subclass, events_with_devices)
            elif subclass in other_subclasses:
                self.generate_class(subclass, others)
            else:  # RDFS, Thing
                self.generate_class(subclass, classes)
        if divide:
            for graph, name in ((products, 'products'), (components, 'components'), (events_with_one_device, 'events with one device'), (events_with_devices, 'events with devices'), (others, 'place, account and benchmark')):
                if name == 'components' or name == 'events with devices':
                    self.generate_graph(graph, (), name)
                else:
                    self.generate_graph(graph, (classes,), name)
        else:
            self.generate_graph(g, (events_with_one_device, products, classes, others,), 'general')

    def generate_graph(self, graph: Digraph, sub_graphs: tuple, name):
        graph.format = self.img_format
        graph.directory = self.directory
        for sub_graph in sub_graphs:
            graph.subgraph(sub_graph)
        graph.render('{} {}'.format(self.file_prefix, name), None, False)
        print('Class diagram {} written.'.format(name))

    @staticmethod
    def initialize_graph(graph: Digraph):
        graph.attr('node', shape='record')

    def generate_class(self, cls, group):
        RDFS._import_schemas = False
        schema = cls.actual_fields()
        if cls != RDFS:
            del schema['@type']
        name = cls.type_name()
        group.node(name, '{{{}|{}}}'.format(name, '\l'.join(self.get_formatted_fields(name, schema, group))))
        try:
            super_class = cls.superclasses(1)[1]
            group.edge(super_class.type_name(), name, arrowtail='empty', arrowhead='none', dir='both')
        except AttributeError:
            pass

    def get_formatted_fields(self, type_name: str, schema: dict, group: Digraph) -> list:
        resulting_fields = []
        for field in self.get_fields(schema, schema_name=type_name):
            name = field['name']
            if 'reference' in field:
                if field['type'] == 'list':
                    head_label = '*' if field['attr']['Required'] else '1..*'
                else:
                    head_label = '1' if field['attr']['Required'] else '0..1'
                group.edge(type_name, field['reference'], headlabel=head_label, taillabel='*', label=field['name'])
            else:
                field['name'] = '*' + name if field['attr']['Unique'] else name
                resulting_field = '+ {}'.format(field['name'])
                if len(field['attr']['Allowed'] or []) > 0:
                    enum_name = '{}Enum'.format(name)
                    group.node(enum_name, '{{{}Enum\lEnum|{}}}'.format(name, '\l'.join(map(str, field['attr']['Allowed']))))
                    resulting_field += ': {}'.format(enum_name)
                else:
                    resulting_field += ': {}'.format(field['type'])
                resulting_field += ' [0..1]' if not field['attr']['Required'] else ''
                resulting_field += ' (write-only)' if field['attr']['Write only'] else ''
                resulting_field += ' (read-only)' if field['attr']['Read only'] else ''
                resulting_fields.append((resulting_field, field['attr']['Sink']))
        resulting_fields.sort(key=Doc.get_sink, reverse=True)
        return [resulting_field[0] for resulting_field in resulting_fields]

