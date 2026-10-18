"""tspack — merged tree-sitter languages exposed through one shared library.

Public API
----------
get_language(name) -> tree_sitter.Language
get_parser(name)   -> tree_sitter.Parser
get_language_names() -> list[str]
"""

from __future__ import annotations
import ctypes
import glob
from importlib.machinery import EXTENSION_SUFFIXES
import os
import sys
from typing import Dict, List

from tree_sitter import Language, Parser


__all__ = [
    "LANGUAGES",
    "get_language",
    "get_parser",
    "get_language_names",
    "has_language",
]

# ---------------------------------------------------------------------------
# Languages expected to be present in the merged .so
# ---------------------------------------------------------------------------
LANGUAGES: List[str] = [
    "bash",
    "c",
    "css",
    "csv",
    "go",
    "html",
    "java",
    "javascript",
    "json",
    "latex",
    "lua",
    "markdown",
    "perl",
    "php",
    "python",
    "query",
    "regex",
    "rst",
    "ruby",
    "rust",
    "sql",
    "toml",
    "vim",
    "xml",
    "yaml",
]


# ---------------------------------------------------------------------------
# Locate and dlopen the merged shared library
# ---------------------------------------------------------------------------
def _find_lib() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for suffix in EXTENSION_SUFFIXES:
        cand = os.path.join(here, "_tspack" + suffix)
        if os.path.exists(cand):
            return cand
    # Fallbacks for unusual build layouts
    for pat in ("_tspack*.so", "_tspack*.dylib", "_tspack*.pyd"):
        hits = glob.glob(os.path.join(here, pat))
        if hits:
            return hits[0]
    raise ImportError(f"tspack native library not found in {here}. Reinstall the package.")


_LIB_PATH = _find_lib()

# RTLD_LOCAL is fine; we resolve symbols from this handle directly.
try:
    _LIB = ctypes.CDLL(_LIB_PATH)
except OSError as exc:  # pragma: no cover
    raise ImportError(f"Could not load {_LIB_PATH}: {exc}") from exc


_LANGUAGE_CACHE: Dict[str, Language] = {}


def _make_language(ptr: int, name: str) -> Language:
    # tree-sitter >=0.23: Language(ptr)
    # tree-sitter 0.22.x: Language(ptr, name)
    try:
        return Language(ptr)  # type: ignore[call-arg]
    except TypeError:
        return Language(ptr, name)  # type: ignore[call-arg]


def _load_language(name: str) -> Language:
    if name in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[name]

    symbol = f"tree_sitter_{name}"
    if not hasattr(_LIB, symbol):
        raise LookupError(
            f"Language '{name}' is not present in {os.path.basename(_LIB_PATH)}. "
            f"Available: {', '.join(get_language_names())}"
        )

    fn = getattr(_LIB, symbol)
    fn.restype = ctypes.c_void_p
    fn.argtypes = []
    ptr = fn()
    if not ptr:
        raise RuntimeError(f"{symbol}() returned NULL")

    lang = _make_language(ptr, name)
    _LANGUAGE_CACHE[name] = lang
    return lang


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_language(name: str) -> Language:
    """Return a cached `tree_sitter.Language` for `name` (e.g. ``"python"``)."""
    return _load_language(name)


def get_parser(name: str) -> Parser:
    """Return a `tree_sitter.Parser` bound to the given language."""
    return Parser(_load_language(name))


def get_language_names() -> List[str]:
    """List the language names actually present in the merged library."""
    out: List[str] = []
    for name in LANGUAGES:
        if hasattr(_LIB, f"tree_sitter_{name}"):
            out.append(name)
    return out


def has_language(name: str) -> bool:
    return hasattr(_LIB, f"tree_sitter_{name}")


# Handy: also expose the native library handle + path for power users
native_library = _LIB
native_library_path = _LIB_PATH


if __name__ == "__main__":  # pragma: no cover
    print("tspack loaded from", _LIB_PATH)
    print("languages:", ", ".join(get_language_names()))
