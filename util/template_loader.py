import os
from pathlib import Path
from typing import Dict, Any
from pybars import Compiler

class TemplateLoader:
    """Utility class for loading and rendering Handlebars templates."""
    
    def __init__(self, templates_dir: str = None):
        """
        Initialize the template loader.
        
        Args:
            templates_dir: Path to templates directory. Defaults to 'templates' in project root.
        """
        if templates_dir is None:
            # Get project root (assuming util is one level deep)
            project_root = Path(__file__).parent.parent
            templates_dir = project_root / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.compiler = Compiler()
        self._cache: Dict[str, Any] = {}
    
    def load_template(self, template_path: str) -> Any:
        """
        Load and compile a Handlebars template.
        
        Args:
            template_path: Relative path to template file from templates directory.
        
        Returns:
            Compiled template function.
        """
        # Check cache first
        if template_path in self._cache:
            return self._cache[template_path]
        
        # Load template file
        full_path = self.templates_dir / template_path
        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            template_source = f.read()
        
        # Compile and cache
        compiled = self.compiler.compile(template_source)
        self._cache[template_path] = compiled
        
        return compiled
    
    def render(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Load and render a Handlebars template with the given context.
        
        Args:
            template_path: Relative path to template file from templates directory.
            context: Dictionary of variables to pass to the template.
        
        Returns:
            Rendered template string.
        """
        template = self.load_template(template_path)
        return template(context)
    
    def clear_cache(self):
        """Clear the template cache."""
        self._cache.clear()


# Global instance for convenience
_default_loader = None

def get_template_loader() -> TemplateLoader:
    """Get the default template loader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = TemplateLoader()
    return _default_loader


def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """
    Convenience function to render a template using the default loader.
    
    Args:
        template_path: Relative path to template file from templates directory.
        context: Dictionary of variables to pass to the template.
    
    Returns:
        Rendered template string.
    """
    loader = get_template_loader()
    return loader.render(template_path, context)
