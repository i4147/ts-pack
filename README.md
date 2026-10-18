# tspack

A single shared object containing many tree-sitter grammars.

## Layout expected

    vendor/
      tree-sitter-python/
        src/parser.c          <- grammar source (required)
        src/scanner.c         <- optional
        dist/*.whl            <- optional fallback if src/ missing
      tree-sitter-go/
      ...

## Build

    pip install build
    python -m build --wheel

The wheel contains `tspack/_tspack.<abi>.so` with every
`tree_sitter_<lang>` entry point merged in.

## Use

    import tspack

    parser = tspack.get_parser("python")
    tree   = parser.parse(b"def hi(): pass")
    print(tree.root_node.sexp())

    print(tspack.get_language_names())