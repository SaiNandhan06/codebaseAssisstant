"""
parse.py — Multi-language AST parser using tree-sitter.

Extracts classes, methods, and functions as Chunk objects from source files.
Supports: Python, JavaScript, TypeScript/TSX, Java, Go.
"""

import os
from dataclasses import dataclass, asdict, field

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

# ── Optional grammars (installed separately) ──────────────────────

try:
    import tree_sitter_typescript as tstypescript
    _HAS_TS = True
except ImportError:
    _HAS_TS = False

try:
    import tree_sitter_java as tsjava
    _HAS_JAVA = True
except ImportError:
    _HAS_JAVA = False

try:
    import tree_sitter_go as tsgo
    _HAS_GO = True
except ImportError:
    _HAS_GO = False


@dataclass
class Chunk:
    id: str
    file_path: str
    language: str
    kind: str
    name: str
    parent: str | None
    start_line: int
    end_line: int
    code: str
    commits: list = field(default_factory=list)
    commit_sha: str | None = None
    repo_url: str | None = None

    def to_dict(self):
        return asdict(self)


# ── Language configuration table ─────────────────────────────────

LANGUAGES = {
    ".py": {
        "name": "python",
        "parser": Parser(Language(tspython.language())),
        "functions": {"function_definition"},
        "classes": {"class_definition"},
    },
    ".js": {
        "name": "javascript",
        "parser": Parser(Language(tsjavascript.language())),
        "functions": {"function_declaration", "function_expression",
                      "arrow_function", "method_definition"},
        "classes": {"class_declaration"},
    },
}

# Add TypeScript/TSX if available
if _HAS_TS:
    _ts_lang = Language(tstypescript.language_typescript())
    _tsx_lang = Language(tstypescript.language_tsx())
    LANGUAGES[".ts"] = {
        "name": "typescript",
        "parser": Parser(_ts_lang),
        "functions": {"function_declaration", "function_expression",
                      "arrow_function", "method_definition"},
        "classes": {"class_declaration"},
    }
    LANGUAGES[".tsx"] = {
        "name": "tsx",
        "parser": Parser(_tsx_lang),
        "functions": {"function_declaration", "function_expression",
                      "arrow_function", "method_definition"},
        "classes": {"class_declaration"},
    }

# Add Java if available
if _HAS_JAVA:
    LANGUAGES[".java"] = {
        "name": "java",
        "parser": Parser(Language(tsjava.language())),
        "functions": {"method_declaration", "constructor_declaration"},
        "classes": {"class_declaration", "interface_declaration", "enum_declaration"},
    }

# Add Go if available
if _HAS_GO:
    LANGUAGES[".go"] = {
        "name": "go",
        "parser": Parser(Language(tsgo.language())),
        "functions": {"function_declaration", "method_declaration"},
        "classes": set(),  # Go doesn't have classes; struct types are detected below
    }


# ── AST walking ──────────────────────────────────────────────────

def _text(source, node):
    return source[node.start_byte:node.end_byte].decode("utf8", errors="replace")


def _get_name(node, source):
    """Returns (name, span_node). Handles `const foo = () => {}` where the name lives on the parent."""
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(source, name_node), node
    parent = node.parent
    if parent is not None and parent.type == "variable_declarator":
        name_node = parent.child_by_field_name("name")
        if name_node is not None:
            return _text(source, name_node), parent
    return None, node

def _walk(node, source, cfg, rel_path, parent_class, chunks):
    # Go struct types (no classes in Go)
    if cfg["name"] == "go" and node.type == "type_declaration":
        for child in node.children:
            if child.type == "type_spec":
                name_node = child.child_by_field_name("name")
                type_node = child.child_by_field_name("type")
                if name_node and type_node and type_node.type == "struct_type":
                    name = _text(source, name_node)
                    chunks.append(_make_chunk(child, source, cfg, rel_path, "class", name, None))
        return

    if node.type in cfg["classes"]:
        name, span = _get_name(node, source)
        if name:
            chunks.append(_make_chunk(span, source, cfg, rel_path, "class", name, parent_class))
        for child in node.children:
            _walk(child, source, cfg, rel_path, name or parent_class, chunks)
        return

    if node.type in cfg["functions"]:
        name, span = _get_name(node, source)
        if name:
            kind = "method" if parent_class else "function"
            chunks.append(_make_chunk(span, source, cfg, rel_path, kind, name, parent_class))
            return  # inner functions are already part of this chunk's code
        # anonymous function: keep descending, it may wrap named functions (e.g. an IIFE)

    for child in node.children:
        _walk(child, source, cfg, rel_path, parent_class, chunks)


def _make_chunk(span, source, cfg, rel_path, kind, name, parent_class):
    start_line = span.start_point[0] + 1
    qualified = f"{parent_class}.{name}" if parent_class and kind == "method" else name
    return Chunk(
        id=f"{rel_path}::{qualified}:{start_line}",
        file_path=rel_path,
        language=cfg["name"],
        kind=kind,
        name=name,
        parent=parent_class if kind == "method" else None,
        start_line=start_line,
        end_line=span.end_point[0] + 1,
        code=_text(source, span),
    )

def parse_file(source: bytes, rel_path: str, ext: str):
    cfg = LANGUAGES[ext]
    tree = cfg["parser"].parse(source)
    chunks = []
    _walk(tree.root_node, source, cfg, rel_path, None, chunks)
    return chunks
