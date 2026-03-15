import os
import json
import re
from typing import Dict, List, Set

class EcosystemDependencyManager:
    """
    Система управления требованиями и зависимостями на масштабе всей экосистемы.
    Позволяет автопилоту автономно обновлять связи между 24 Суверенными Деревьями.
    """
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self.registry_file = os.path.join(root_dir, "ecosystem_dependency_graph.json")
        self.graph: Dict[str, List[str]] = {}
        self.load_graph()

    def load_graph(self):
        """Загружает текущую карту зависимостей."""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                self.graph = json.load(f)

    def save_graph(self):
        """Сохраняет обновленную карту зависимостей."""
        with open(self.registry_file, 'w') as f:
            json.dump(self.graph, f, indent=2)

    def scan_tree_imports(self, tree_path: str) -> Set[str]:
        """Сканирует исходный код 'Дерева' на наличие импортов других органов или библиотек."""
        found_imports = set()
        for root, dirs, files in os.walk(tree_path):
            for file in files:
                if file.endswith(".py"):
                    try:
                        with open(os.path.join(root, file), 'r') as f:
                            content = f.read()
                            matches = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_\.]+)", content, re.MULTILINE)
                            for m in matches:
                                root_mod = m.split('.')[0]
                                if root_mod not in ["os", "sys", "json", "re", "time", "datetime", "typing", "asyncio"]:
                                    found_imports.add(root_mod)
                    except Exception:
                        continue
        return found_imports

    def sync_requirements(self, tree_id: str, new_deps: List[str]):
        """Автоматическое обновление requirements.txt для конкретного органа."""
        tree_path = os.path.join(self.root_dir, tree_id)
        if not os.path.isdir(tree_path):
            return
            
        req_file = os.path.join(tree_path, "requirements.txt")
        current_deps = set()
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                current_deps = {line.strip() for line in f if line.strip() and not line.startswith("#")}
        
        merged_deps = sorted(list(current_deps.union(set(new_deps))))
        
        with open(req_file, 'w') as f:
            f.write(f"# Auto-updated by Autopilot for {tree_id}\n")
            for dep in merged_deps:
                f.write(f"{dep}\n")

    def scan_all_trees(self, trees: List[str]):
        """Сканирует все указанные деревья и строит граф зависимостей."""
        for tree in trees:
            if os.path.isdir(tree):
                deps = list(self.scan_tree_imports(tree))
                self.graph[tree] = deps
                self.sync_requirements(tree, deps)

if __name__ == "__main__":
    manager = EcosystemDependencyManager()
    target_trees = ["core", "map", "gov", "security", "identity", "nexus", "transport", "flow", "devkit"]
    manager.scan_all_trees(target_trees)
    print(f"Ecosystem Dependency Graph Updated: {json.dumps(manager.graph, indent=2)}")
    manager.save_graph()
