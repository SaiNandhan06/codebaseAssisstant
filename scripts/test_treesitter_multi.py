import os
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())

py_parser = Parser(PY_LANGUAGE)
js_parser = Parser(JS_LANGUAGE)

FUNCTION_NODE_TYPES = {
    ".py" : ["function_definition"],
    ".js" : ["function_declaration", "function_expression", "arrow_function"],
}

def get_parser_for_file(file_path):
    ext = os.path.splitext(file_path)[1]
    if ext == ".py":
        return py_parser, ext
    elif ext == ".js":
        return js_parser, ext
    return None, ext

def extract_functions(node, source_code, node_types):
    functions = []
    if node.type in node_types:
        name_node = node.child_by_field_name("name")
        name = source_code[name_node.start_byte:name_node.end_byte].decode("utf8") if name_node else "(anonymous)"
        functions.append({
            "name": name,
            "start_line": node.start_point[0] + 1,
            "end_line":node.end_point[0] + 1,
        })
    for child in node.children:
        functions.extend(extract_functions(child, source_code, node_types))
    return functions

CLONE_PATH = r"C:\Users\M Sainandhan\OneDrive\Documents\Projects\newQRGenerator"

for root, dirs, files in os.walk(CLONE_PATH):
    dirs[:] = [d for d in dirs if d != ".git"]
    for file in files:
        file_path = os.path.join(root, file)
        parser, ext = get_parser_for_file(file_path)

        if parser is None:
            print(f"[skip] {file} - no parser for '{ext}' files yet")
            continue
        with open(file_path,"rb") as f:
            source_code = f.read()

        tree = parser.parse(source_code)
        functions = extract_functions(tree.root_node, source_code, FUNCTION_NODE_TYPES[ext])

        print(f"\n[{ext}] {file} - found {len(functions)} function(s)")
        for fn in functions:
            print(f"  - {fn['name']} (lines {fn['start_line']}-{fn['end_line']})")
