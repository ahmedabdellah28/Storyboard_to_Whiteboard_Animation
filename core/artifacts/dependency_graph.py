"""Directed Acyclic Graph (DAG) for task dependencies and intelligent cache invalidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class DependencyNode:
    task_id: str
    component: str
    dependencies: Set[str] = field(default_factory=set)
    outputs: List[str] = field(default_factory=list)
    resource_type: str = "DEFAULT"  # NETWORK_API, CPU_HEAVY, GPU_RENDER, DISK_IO


class DependencyGraph:
    """Manages stage dependencies and calculates cascading invalidations."""

    def __init__(self) -> None:
        self.nodes: Dict[str, DependencyNode] = {}
        self._reverse_deps: Dict[str, Set[str]] = {}

    def add_node(
        self,
        task_id: str,
        component: str,
        dependencies: Optional[Set[str]] = None,
        outputs: Optional[List[str]] = None,
        resource_type: str = "DEFAULT",
    ) -> DependencyNode:
        deps = dependencies or set()
        node = DependencyNode(
            task_id=task_id,
            component=component,
            dependencies=set(deps),
            outputs=outputs or [],
            resource_type=resource_type,
        )
        self.nodes[task_id] = node

        # Update reverse dependencies (downstream nodes dependent on this node)
        for dep in deps:
            if dep not in self._reverse_deps:
                self._reverse_deps[dep] = set()
            self._reverse_deps[dep].add(task_id)

        return node

    def get_dependencies(self, task_id: str) -> Set[str]:
        node = self.nodes.get(task_id)
        return set(node.dependencies) if node else set()

    def get_dependents(self, task_id: str) -> Set[str]:
        """Return all direct downstream tasks that depend on task_id."""
        return set(self._reverse_deps.get(task_id, set()))

    def get_transitive_dependents(self, task_id: str) -> Set[str]:
        """Compute the full transitive closure of downstream tasks affected if task_id changes."""
        affected: Set[str] = set()
        queue = list(self.get_dependents(task_id))

        while queue:
            curr = queue.pop(0)
            if curr not in affected:
                affected.add(curr)
                for child in self.get_dependents(curr):
                    if child not in affected:
                        queue.append(child)

        return affected

    def get_execution_order(self) -> List[str]:
        """Topological sort of tasks to determine safe parallel/serial execution order."""
        in_degree = {k: len(v.dependencies) for k, v in self.nodes.items()}
        queue = [k for k, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for dependent in self.get_dependents(node):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self.nodes):
            unresolved = set(self.nodes.keys()) - set(order)
            raise ValueError(f"Cyclic dependency detected among nodes: {unresolved}")

        return order


def build_default_section_dag(section_id: str) -> DependencyGraph:
    """Build the canonical production DAG for a whiteboard section."""
    dag = DependencyGraph()

    # Audio branch
    dag.add_node(f"{section_id}_tts", component="tts", dependencies=set(), resource_type="NETWORK_API")
    dag.add_node(f"{section_id}_whisper", component="whisper", dependencies={f"{section_id}_tts"}, resource_type="CPU_HEAVY")

    # Visual branch
    dag.add_node(f"{section_id}_extraction", component="extraction", dependencies=set(), resource_type="CPU_HEAVY")
    dag.add_node(f"{section_id}_layout", component="layout", dependencies={f"{section_id}_extraction"}, resource_type="CPU_HEAVY")

    # Sync branch
    dag.add_node(f"{section_id}_sync", component="sync", dependencies={f"{section_id}_whisper", f"{section_id}_layout"}, resource_type="CPU_HEAVY")
    dag.add_node(f"{section_id}_sfx", component="sfx", dependencies={f"{section_id}_sync"}, resource_type="CPU_HEAVY")

    # Audio Mix & Video Render
    dag.add_node(f"{section_id}_audio_mix", component="audio_mix", dependencies={f"{section_id}_tts", f"{section_id}_sfx"}, resource_type="DISK_IO")
    dag.add_node(f"{section_id}_render", component="render", dependencies={f"{section_id}_sync", f"{section_id}_extraction"}, resource_type="GPU_RENDER")

    # Final Mux / Deliverable
    dag.add_node(f"{section_id}_deliverable", component="deliverable", dependencies={f"{section_id}_render", f"{section_id}_audio_mix"}, resource_type="DISK_IO")

    return dag
