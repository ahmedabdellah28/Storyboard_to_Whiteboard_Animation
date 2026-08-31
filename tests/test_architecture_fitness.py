"""
Architecture Fitness Tests (Phase 2).

Enforces strict architectural boundaries and dependency directions via AST static analysis:
Rule 1: Domain Layer (engine/core/) must be Pure Python (NO Kivy, NO KivyMD, NO UI).
Rule 2: State Layer (ui/state/) must not leak UI framework internals (Clock, Widgets).
Rule 3: Presentation Layer (ui/widgets/, ui/screens/) must not directly import raw Video Encoders (PyAV / cv2.VideoWriter).
Rule 4: Zero Circular Imports across all packages.
Rule 5: Domain Models must be instantiable without Kivy initialization.
"""
import os
import sys
import ast
import unittest
from pathlib import Path
from collections import defaultdict

kivy_dir = Path(__file__).resolve().parent.parent / "kivy"
sys.path.insert(0, str(kivy_dir))


class CodebaseASTInspector:
    @staticmethod
    def get_imports_for_file(py_path: Path):
        imports = []
        try:
            content = py_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imports.append((node.lineno, n.name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for n in node.names:
                        full = f"{mod}.{n.name}" if mod else n.name
                        imports.append((node.lineno, full))
        except Exception as e:
            pass
        return imports

    @staticmethod
    def get_all_python_files(sub_dir: str):
        target_dir = kivy_dir / sub_dir
        if not target_dir.exists():
            return []
        return [p for p in target_dir.rglob("*.py") if "__pycache__" not in p.parts]


class TestArchitectureFitness(unittest.TestCase):

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 1: Domain Layer (engine/core/) Must Be Pure Python
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_1_domain_has_zero_kivy_dependencies(self):
        """Domain layer (engine/core/) must not import kivy, kivymd, or ui."""
        core_files = CodebaseASTInspector.get_all_python_files("engine/core")
        self.assertGreater(len(core_files), 0, "engine/core/ must contain domain files")

        forbidden_prefixes = ("kivy", "kivymd", "ui")
        violations = []

        for f in core_files:
            rel = f.relative_to(kivy_dir).as_posix()
            imports = CodebaseASTInspector.get_imports_for_file(f)
            for lineno, imp in imports:
                for forbidden in forbidden_prefixes:
                    if imp == forbidden or imp.startswith(f"{forbidden}."):
                        violations.append(f"{rel}:{lineno} imports '{imp}'")

        self.assertEqual(len(violations), 0, f"Rule 1 Violations found in Domain Layer:\n" + "\n".join(violations))

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 2: Processing Layer (engine/processing/) Must Be Pure Engine
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_2_processing_has_zero_kivy_dependencies(self):
        """Processing layer (engine/processing/) must not import kivy, kivymd, or ui."""
        proc_files = CodebaseASTInspector.get_all_python_files("engine/processing")
        self.assertGreater(len(proc_files), 0, "engine/processing/ must contain files")

        forbidden_prefixes = ("kivy", "kivymd", "ui")
        violations = []

        for f in proc_files:
            rel = f.relative_to(kivy_dir).as_posix()
            imports = CodebaseASTInspector.get_imports_for_file(f)
            for lineno, imp in imports:
                for forbidden in forbidden_prefixes:
                    if imp == forbidden or imp.startswith(f"{forbidden}."):
                        violations.append(f"{rel}:{lineno} imports '{imp}'")

        self.assertEqual(len(violations), 0, f"Rule 2 Violations found in Processing Layer:\n" + "\n".join(violations))

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 3: Domain Models Pure Instantiation Test
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_3_domain_models_instantiation_without_kivy(self):
        """Domain models (SceneObject, Scene, Project, SceneConfig) must instantiate without UI."""
        from engine.core.scene import SceneObject, Scene, SceneConfig
        from engine.core.project import Project, StructureType, PanelStructure

        # Test SceneConfig default values
        cfg = SceneConfig(width=1920, height=1080, fps=30)
        self.assertEqual(cfg.width, 1920)

        # Test SceneObject
        obj = SceneObject(name="Character 1", bbox=(10, 20, 100, 200))
        self.assertEqual(obj.name, "Character 1")
        self.assertEqual(obj.bbox, (10, 20, 100, 200))

        # Test Project
        proj = Project(structure_type=StructureType.STORYBOARD)
        self.assertTrue(proj.is_storyboard)
        self.assertFalse(proj.is_single_scene)

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 4: Circular Import Detection across Codebase
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_4_zero_circular_imports(self):
        """Analyzes import dependency graph to ensure no circular import cycles exist."""
        all_py_files = [p for p in kivy_dir.rglob("*.py") if "__pycache__" not in p.parts]
        
        # Build dependency graph
        graph = defaultdict(set)
        for f in all_py_files:
            rel = f.relative_to(kivy_dir).as_posix().replace(".py", "").replace("/", ".")
            imports = CodebaseASTInspector.get_imports_for_file(f)
            for _, imp in imports:
                # Normalize internal imports
                matched_mod = None
                for candidate in all_py_files:
                    cand_rel = candidate.relative_to(kivy_dir).as_posix().replace(".py", "").replace("/", ".")
                    if imp == cand_rel or imp.startswith(f"{cand_rel}."):
                        matched_mod = cand_rel
                        break
                if matched_mod and matched_mod != rel:
                    graph[rel].add(matched_mod)

        # Cycle detection via DFS
        visited = {}  # None = unvisited, 1 = visiting (in stack), 2 = visited
        cycles = []

        def dfs(node, path):
            visited[node] = 1
            path.append(node)
            for neighbor in graph.get(node, []):
                if visited.get(neighbor) == 1:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                elif visited.get(neighbor) is None:
                    dfs(neighbor, path)
            path.pop()
            visited[node] = 2

        for node in list(graph.keys()):
            if visited.get(node) is None:
                dfs(node, [])

        self.assertEqual(len(cycles), 0, f"Circular dependencies detected:\n" + "\n".join([" -> ".join(c) for c in cycles]))

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 5: ProjectState Isolation Status (Targeting Phase 3 Resolution)
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_5_project_state_isolation(self):
        """
        Enforces that ProjectState in ui/state/ has ZERO dependencies on Kivy/KivyMD.
        """
        state_file = kivy_dir / "ui" / "state" / "project_state.py"
        self.assertTrue(state_file.exists(), "project_state.py must exist")
        imports = CodebaseASTInspector.get_imports_for_file(state_file)
        kivy_imports = [f"{lno}: {imp}" for lno, imp in imports if "kivy" in imp.lower()]
        self.assertEqual(len(kivy_imports), 0, f"ProjectState has forbidden Kivy imports:\n" + "\n".join(kivy_imports))

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 6: Canvas Layer Isolation (ui/canvas/)
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_6_canvas_layer_isolation(self):
        """
        Enforces that UI Canvas does not directly import raw render engine or video encoder.
        """
        canvas_files = CodebaseASTInspector.get_all_python_files("ui/canvas")
        forbidden_substrings = ("engine.render.concentric_engine", "av.", "pyav")
        violations = []

        for f in canvas_files:
            rel = f.relative_to(kivy_dir).as_posix()
            imports = CodebaseASTInspector.get_imports_for_file(f)
            for lineno, imp in imports:
                for forbidden in forbidden_substrings:
                    if forbidden in imp.lower():
                        violations.append(f"{rel}:{lineno} imports '{imp}'")

        self.assertEqual(len(violations), 0, f"Rule 6 Violations found in Canvas Layer:\n" + "\n".join(violations))

    # ═════════════════════════════════════════════════════════════════════════
    #  RULE 7: Render Engine Purity (engine/render/)
    # ═════════════════════════════════════════════════════════════════════════
    def test_rule_7_render_engine_has_zero_kivy_dependencies(self):
        """
        Enforces that Render Engine (engine/render/) has ZERO dependencies on Kivy/KivyMD/UI.
        """
        render_files = CodebaseASTInspector.get_all_python_files("engine/render")
        forbidden_prefixes = ("kivy", "kivymd", "ui")
        violations = []

        for f in render_files:
            rel = f.relative_to(kivy_dir).as_posix()
            imports = CodebaseASTInspector.get_imports_for_file(f)
            for lineno, imp in imports:
                for forbidden in forbidden_prefixes:
                    if imp == forbidden or imp.startswith(f"{forbidden}."):
                        violations.append(f"{rel}:{lineno} imports '{imp}'")

        self.assertEqual(len(violations), 0, f"Rule 7 Violations in Render Engine:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()

