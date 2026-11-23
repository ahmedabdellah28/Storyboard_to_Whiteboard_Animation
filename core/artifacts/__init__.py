"""Artifacts management package."""

from core.artifacts.artifact_identity import (
    compute_artifact_hash,
    hash_dict,
    hash_file,
    hash_string,
)
from core.artifacts.artifact_store import (
    ArtifactRecord,
    ArtifactStore,
    get_artifact_store,
)
from core.artifacts.cache_validator import (
    CacheValidator,
)
from core.artifacts.dependency_graph import (
    DependencyGraph,
    DependencyNode,
    build_default_section_dag,
)
from core.artifacts.revision_manager import (
    RevisionManager,
    get_revision_manager,
)

__all__ = [
    "compute_artifact_hash",
    "hash_file",
    "hash_string",
    "hash_dict",
    "ArtifactRecord",
    "ArtifactStore",
    "get_artifact_store",
    "CacheValidator",
    "DependencyNode",
    "DependencyGraph",
    "build_default_section_dag",
    "RevisionManager",
    "get_revision_manager",
]
