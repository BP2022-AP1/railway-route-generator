from typing import List
from yaramo.model import Edge, Route
from yaramo.signal import SignalDirection, SignalFunction
from yaramo.topology import Topology


class RouteGenerator(object):
    def __init__(self, topology):
        self.topology: Topology = topology

    def traverse_edge(
        self, edge: Edge, direction, current_route=None, active_signal=None
    ) -> List[Route]:
        signals_on_edge_in_direction = edge.get_signals_with_direction_in_order(
            direction
        )

        if (len(signals_on_edge_in_direction) == 0):
            return # No signals on this edge, so no start
        
        active_signal = signals_on_edge_in_direction[0]
        current_route = Route(active_signal, maximum_speed=edge.maximum_speed)

        for signal in signals_on_edge_in_direction[1:]:
            if (
                active_signal.function != signal.function
                or active_signal.function == SignalFunction.Block_Signal
            ):
                # Route ends at signal
                current_route.end_signal = signal
                self.routes.append(current_route)
                # And start the next route from this signal
                active_signal = signal
                current_route = Route(signal, maximum_speed=edge.maximum_speed)
            else:
                # Next signal is from the same kind, error
                raise ValueError(
                    "The topology contains two Einfahr_Signals or two Ausfahr_Signals in a row"
                )

        next_node = edge.node_b
        if direction == SignalDirection.GEGEN:
            next_node = edge.node_a

        possible_followers = next_node.get_possible_followers(edge)
        for next_edge in possible_followers:
            next_direction = next_edge.get_direction_based_on_start_node(
                next_node
            )
            self.traverse_edge_until_next_signals(
                next_edge, next_direction, current_route.duplicate(), active_signal
            )
    
    def traverse_edge_until_next_signals(
        self, edge: Edge, direction, current_route, active_signal
    ):
        if edge in current_route.edges: # we are walking in a loop
            return
        
        current_route.edges.append(edge)
        if edge.maximum_speed is not None and (
            edge.maximum_speed < current_route.maximum_speed
        ):
            current_route.maximum_speed = edge.maximum_speed
        
        signals_on_edge_in_direction = edge.get_signals_with_direction_in_order(
            direction
        )

        if (len(signals_on_edge_in_direction) != 0):
            current_route.end_signal = signals_on_edge_in_direction[0]
            self.routes.append(current_route)
            return
        
        next_node = edge.node_b
        if direction == SignalDirection.GEGEN:
            next_node = edge.node_a

        possible_followers = next_node.get_possible_followers(edge)
        for next_edge in possible_followers:
            next_direction = next_edge.get_direction_based_on_start_node(
                next_node
            )
            self.traverse_edge_until_next_signals(
                next_edge, next_direction, current_route.duplicate(), active_signal
            )

    def generate_routes(self):
        self.routes = []
        for edge in self.topology.edges.values():
            self.traverse_edge(edge, SignalDirection.IN)
            self.traverse_edge(edge, SignalDirection.GEGEN)

        # Filter duplicates
        filtered_routes = []
        for route in self.routes:
            should_be_added = True
            if route.start_signal.uuid == route.end_signal.uuid:
                should_be_added = False
            else:
                for filtered_route in filtered_routes:
                    if (
                        route.start_signal.uuid == filtered_route.start_signal.uuid
                        and route.end_signal.uuid == filtered_route.end_signal.uuid
                    ):
                        if route.get_length() < filtered_route.get_length():
                            filtered_routes.remove(filtered_route)
                        else:
                            should_be_added = False
            if should_be_added:
                filtered_routes.append(route)

        self.topology.routes = {route.uuid: route for route in self.routes}
