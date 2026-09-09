import glob
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger("promptforge.core.prompt_registry")

DEFAULT_PROMPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompts")
)

class PromptRegistry:
    """
    Loads and manages system prompt templates from external versioned text files in prompts/.
    Allows dynamic loading, variable interpolation, and hot reloading.
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self._cache: Dict[str, str] = {}
        os.makedirs(self.prompts_dir, exist_ok=True)

    def reload(self):
        """Clears cached prompts so edits on disk take immediate effect."""
        self._cache.clear()

    def get_prompt(self, prompt_name: str, /) -> str:
        """
        Loads prompt content for a given name (e.g. 'chain_1_intent_decomposition').
        Checks for .txt or .md files.
        """
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        candidate_extensions = [".txt", ".md", ""]
        content: Optional[str] = None

        for ext in candidate_extensions:
            filename = f"{prompt_name}{ext}"
            filepath = os.path.join(self.prompts_dir, filename)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                break

        if content is None:
            raise FileNotFoundError(
                f"Prompt template '{prompt_name}' not found in directory: {self.prompts_dir}"
            )

        self._cache[prompt_name] = content
        return content

    def render(self, prompt_name: str, /, **kwargs) -> str:
        """
        Loads prompt template and interpolates keyword arguments safely.
        Positional-only prompt_name avoids collision with kwargs like name='...'.
        """
        template = self.get_prompt(prompt_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing variable {e} when rendering prompt '{prompt_name}'. Using safe replace.")
            rendered = template
            for k, v in kwargs.items():
                rendered = rendered.replace(f"{{{k}}}", str(v))
            return rendered

    def list_available_prompts(self) -> List[str]:
        """Lists all prompt templates present in the prompts directory."""
        files = glob.glob(os.path.join(self.prompts_dir, "*.*"))
        names = []
        for f in files:
            base = os.path.basename(f)
            if not base.startswith("."):
                name_without_ext = os.path.splitext(base)[0]
                names.append(name_without_ext)
        return sorted(list(set(names)))

_default_registry: Optional[PromptRegistry] = None

def get_prompt_registry() -> PromptRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = PromptRegistry()
    return _default_registry
