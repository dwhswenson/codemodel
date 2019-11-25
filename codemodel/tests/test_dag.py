import pytest

import functools

from codemodel.dag import *


class TestDAG(object):
    def setup(self):
        # EXAMPLE DAG
        # b-----\
        #  > d   > f
        # c   > e
        #    a
        #          g
        self.edges = ["bd", "cd", "ae", "de", "bf", "ef"]
        self.nodes = "abcdefg"
        self.dag = DAG()
        for edge in self.edges:
            self.dag.register_edge(edge)

        for node in self.nodes:
            self.dag.register_node(node)

    def test_dag_setup(self):
        assert self.dag.nodes == set(self.nodes)
        edges = set(Edge(*e) for e in self.edges)
        assert self.dag.edges == edges

    def test_register_edge(self):
        dag = DAG()
        dag.register_edge("ab")
        assert dag.edges == {Edge('a', 'b')}
        assert dag.nodes == {'a', 'b'}

    def test_register_node(self):
        dag = DAG()
        dag.register_node("a")
        assert dag.edges == set([])
        assert dag.nodes == {'a'}

    @pytest.mark.parametrize("to_from", ["to", "from"])
    def test_from_dependency_dict(self, to_from):
        deps = {'a': [], 'b': [], 'c': [], 'd': ['b', 'c'], 'e': ['d', 'a'],
                'f': ['b', 'e'], 'g': []}
        dag = DAG.from_dependency_dict(deps, to_from)
        expected_edges = {
            'to': set(Edge(*e) for e in self.edges),
            'from': set(Edge(*reversed(e)) for e in self.edges)
        }[to_from]
        assert set(dag.nodes) == set(self.nodes)
        assert set(dag.edges) == set(expected_edges)

    def test_build_node_counts(self):
        n_from = {'a': 1, 'b': 2, 'c': 1, 'd': 1, 'e': 1, 'f': 0, 'g': 0}
        n_to = {'a': 0, 'b': 0, 'c': 0, 'd': 2, 'e': 2, 'f': 2, 'g': 0}
        from_counts, to_counts = self.dag._build_node_counts()
        assert from_counts == n_from
        assert to_counts == n_to

    def assert_dag_order(self, ordered):
        assert ordered.index('b') < ordered.index('d')
        assert ordered.index('c') < ordered.index('d')
        assert ordered.index('a') < ordered.index('e')
        assert ordered.index('d') < ordered.index('e')
        assert ordered.index('b') < ordered.index('f')
        assert ordered.index('e') < ordered.index('f')

    def test_ordered_no_callback(self):
        ordered = list(self.dag.ordered())
        assert set(ordered) == self.dag.nodes
        self.assert_dag_order(ordered)

    @pytest.mark.parametrize("callback, expected", [
        (sorted, "abcdefg"),
        (lambda x: sorted(x, reverse=True), "gcbdaef"),
    ])
    def test_ordered(self, callback, expected):
        ordered = list(self.dag.ordered(callback))
        assert "".join(ordered) == expected
