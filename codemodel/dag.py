import collections

Edge = collections.namedtuple("Edge", "from_node to_node")

class DAG(object):
    """Directed acyclic graph, with topological ordering.

    The node ordering used here allows the user to provide a custom callback
    to select between topologically accessible nodes, allowing some
    customization of the order that nodes are returned.

    Use :method:`.register_edge` and :method:`.register_node` to build the
    graph. Registering edges automatically registers associated nodes.
    """
    def __init__(self):
        self.edges = set([])
        self.nodes = set([])

    def register_edge(self, edge):
        """Add an edge to the graph.

        Parameters
        ----------
        edge : Tuple[Any,Any]
            Nodes connected by the edge in the format (From, To). Internally
            this will be converted to an Edge namedtuple. Any new nodes are
            automatically registered.
        """
        edge = Edge(*edge)
        self.edges.update({edge})
        self.register_node(edge.from_node)
        self.register_node(edge.to_node)

    def register_node(self, node):
        """Add a node to the graph

        Parameters
        ----------
        node : Any
            Node to add.
        """
        self.nodes.update({node})

    @classmethod
    def from_dependency_dict(cls, dependencies, keys="to"):
        """Create a DAG from a dictionary of dependencies.

        Parameters
        ----------
        dependencies : Dict[Any, List[Any]]
            dependency chart; directed edges defined between the key each
            element in the associated lit of values
        keys : str
            "to" or "from" depending on whether the keys of the dependency
            dictionary are the "to" nodes (default) or the "from" nodes

        Returns
        -------
        :class:`.DAG` :
            resulting DAG
        """
        edge_maker = {
            "to": lambda k, v: Edge(v, k),
            "from": lambda k, v: Edge(k, v)
        }[keys]
        bare_nodes = [k for k in dependencies if dependencies[k] == []]
        edges = [
            edge_maker(key_node, val_node)
            for key_node, deps in dependencies.items()
            for val_node in deps
        ]

        dag = cls()
        for edge in edges:
            dag.register_edge(edge)

        for node in bare_nodes:
            dag.register_node(node)

        return dag


    def _build_node_counts(self):
        def node_counter(node_list):
            counts = collections.Counter(node_list)
            missing_nodes = self.nodes - set(counts.keys())
            for node in missing_nodes:
                counts[node] = 0
            return counts

        from_counts = node_counter([e.from_node for e in self.edges])
        to_counts = node_counter([e.to_node for e in self.edges])
        return from_counts, to_counts

    def _pop_node(self, node, to_counts):
        edges = [edge for edge in self.edges if edge.from_node == node]
        for edge in edges:
            to_counts[edge.to_node] -= 1
        del to_counts[node]
        return node

    def ordered(self, sort_callback=None):
        """Generator to iterate over DAG in build order.

        Parameters
        ----------
        sort_callback : Union[Callable[[List], List], None]
            function that takes a list of nodes and returns the preferred
            order for them; used when DAG order isn't unique
        """
        if sort_callback is None:
            sort_callback = lambda x: x

        _, to_counts = self._build_node_counts()

        while len(to_counts):
            assert all(val >= 0 for val in to_counts.values())
            zero_count = [node for node in to_counts
                          if to_counts[node] == 0]
            ordered = sort_callback(zero_count)
            popped = self._pop_node(ordered[0], to_counts)
            yield popped
