from __future__ import annotations
import os
from pathlib import Path
import shutil
import sys
import zipfile

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext as _build_ext


HERE = Path(__file__).parent.resolve()
VENDOR = HERE / "vendor"
CSRC = HERE / "csrc"

# Directories to ignore when walking a grammar's src/
_IGNORE_DIRS = {"node_modules", "obj", "build", "__pycache__"}


def _lang_from_dir(name: str) -> str:
    return name[len("tree-sitter-") :] if name.startswith("tree-sitter-") else name


def _iter_src_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _IGNORE_DIRS for part in p.parts):
            continue
        if p.suffix in (".c", ".cc", ".cpp", ".cxx"):
            yield p


def _extract_wheel_sources(lang_dir: Path) -> Path | None:
    """Fallback: unpack a wheel and look for parser.c."""
    dist = lang_dir / "dist"
    if not dist.is_dir():
        return None
    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        return None

    out = lang_dir / "_wheel_extracted"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    with zipfile.ZipFile(wheels[0]) as zf:
        zf.extractall(out)

    # typical wheel layout: pkg/_binding*.so, and grammar source sometimes
    # shipped under pkg/src/parser.c or src/parser.c
    for parser in out.rglob("parser.c"):
        return parser.parent
    return None


def collect_sources_and_includes():
    sources: list[str] = []
    include_dirs: list[str] = []
    missing: list[str] = []

    if not VENDOR.is_dir():
        raise SystemExit(f"vendor/ not found at {VENDOR}")

    for lang_dir in sorted(VENDOR.iterdir()):
        if not lang_dir.is_dir():
            continue
        if not lang_dir.name.startswith("tree-sitter-"):
            continue

        src = lang_dir / "src"
        if not src.is_dir():
            src = _extract_wheel_sources(lang_dir)

        if src is None or not src.is_dir():
            missing.append(lang_dir.name)
            continue

        include_dirs.append(str(src))
        found_any = False
        for f in _iter_src_files(src):
            sources.append(str(f))
            found_any = True
        if not found_any:
            missing.append(lang_dir.name)

    if missing:
        print(f"[tspack] WARNING: no sources found for: {', '.join(missing)}", file=sys.stderr)
    if not sources:
        raise SystemExit(
            "[tspack] No C/C++ grammar sources found in vendor/. "
            "Place each grammar under vendor/tree-sitter-<lang>/src/."
        )
    return sources, include_dirs


class build_ext(_build_ext):
    """Collect sources lazily, right before compilation."""

    def build_extensions(self):  # noqa: N802
        sources, include_dirs = collect_sources_and_includes()
        stub = CSRC / "stub.c"
        if not stub.is_file():
            raise SystemExit(f"[tspack] Missing {stub}")
        sources.append(str(stub))

        has_cxx = any(s.endswith((".cc", ".cpp", ".cxx")) for s in sources)
        language = "c++" if has_cxx else "c"

        extra_compile_args: list[str] = []
        if os.name == "posix":
            # Make sure `tree_sitter_<lang>` symbols land in the dynamic
            # symbol table so ctypes can find them.
            extra_compile_args += ["-fvisibility=default", "-O2"]
        elif os.name == "nt":
            extra_compile_args += ["/O2"]
        # else: let the platform pick defaults.

        self.extensions = [
            Extension(
                "tspack._tspack",
                sources=sources,
                include_dirs=include_dirs,
                extra_compile_args=extra_compile_args,
                language=language,
            )
        ]
        super().build_extensions()


if __name__ == "__main__":
    setup(cmdclass={"build_ext": build_ext})
