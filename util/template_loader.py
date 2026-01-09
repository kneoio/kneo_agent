import os
from pathlib import Path
from typing import Dict, Any
from pybars import Compiler


class TemplateLoader:

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            project_root = Path(__file__).parent.parent
            templates_dir = project_root / "templates"

        self.templates_dir = Path(templates_dir)
        self.compiler = Compiler()
        self._cache: Dict[str, Any] = {}

    def load_template(self, template_path: str) -> Any:

        if template_path in self._cache:
            return self._cache[template_path]

        full_path = self.templates_dir / template_path
        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            template_source = f.read()

        compiled = self.compiler.compile(template_source)
        self._cache[template_path] = compiled

        return compiled

    def render(self, template_path: str, context: Dict[str, Any]) -> str:
        template = self.load_template(template_path)
        return template(context)

    def clear_cache(self):
        self._cache.clear()


_default_loader = None


def get_template_loader() -> TemplateLoader:
    global _default_loader
    if _default_loader is None:
        _default_loader = TemplateLoader()
    return _default_loader


def render_template(template_path: str, context: Dict[str, Any]) -> str:
    loader = get_template_loader()
    return loader.render(template_path, context)


def template_exists(template_path: str) -> bool:
    loader = get_template_loader()
    full_path = loader.templates_dir / template_path
    return full_path.exists()
