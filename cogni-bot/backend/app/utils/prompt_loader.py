import os
from functools import lru_cache

# Get the absolute path to the 'prompts' directory
PROMPT_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..', 'prompts')


@lru_cache(maxsize=32)
def _load_prompt_file(file_path: str) -> str:
    """
    Internal function to read a prompt file from disk.
    Uses lru_cache to cache file contents in memory after the first read.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found at: {file_path}")
    except Exception as e:
        raise IOError(f"Error reading prompt file {file_path}: {e}")


def get_prompt(prompt_name: str, **kwargs) -> str:
    """
    Loads a prompt from a file and formats it with the given keyword arguments.

    Example:
    get_prompt("analysis/ba_summary.txt", user_query="...", table_data="...")

    Args:
        prompt_name: The relative path to the prompt file within the 'prompts' directory.
        **kwargs: Variables to format into the prompt string.

    Returns:
        The fully formatted prompt string.
    """
    full_path = os.path.join(PROMPT_DIR, prompt_name)

    # Load the raw template from the file (this will be cached)
    template = _load_prompt_file(full_path)

    # Format the template with the provided variables
    if kwargs:
        return template.format(**kwargs)

    return template
