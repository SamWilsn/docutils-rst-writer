import sys
from typing import Optional

import atheris

with atheris.instrument_imports():
    import docutils
    import docutils.writers
    import docutils.core  # noqa: F401
    from docutils import nodes
    from docutils.parsers.rst import Parser

    from docutils_rst_writer.writer import Writer

from docutils.core import publish_string
from docutils.frontend import OptionParser
from docutils.utils import new_document


@atheris.instrument_func
def parse_rst(text: str) -> nodes.document:
    parser = Parser()
    components = (Parser,)
    settings = OptionParser(components=components).get_default_values()
    settings.halt_level = 0
    document = new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


@atheris.instrument_func
def write_rst(doc: nodes.document) -> Optional[str]:
    writer = Writer()
    writer.document = doc
    writer.translate()
    return writer.output


def fuzz_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    src = fdp.ConsumeUnicodeNoSurrogates(sys.maxsize)

    if "\x00" in src:
        return

    try:
        doc = parse_rst(src)
    except:  # noqa: E722
        return

    wrote = write_rst(doc)
    assert wrote is not None

    wrote_publish = publish_string(wrote).decode("utf-8")
    wrote_tree_str = str(parse_rst(wrote))

    src_pubilsh = publish_string(src).decode("utf-8")
    src_tree_str = str(doc)

    if wrote_publish != src_pubilsh and wrote_tree_str != src_tree_str:
        print("Original Doc:\n\n" + src_tree_str, end="\n\n")
        print("Rewritten Doc:\n\n" + wrote_tree_str, end="\n\n")

        print("Original Publish:\n\n" + src_pubilsh, end="\n\n")
        print("Rewritten Publish:\n\n" + src_pubilsh, end="\n\n")

        print("Original rST:\n\n" + src, end="\n\n")
        print("Rewritten rST:\n\n" + wrote, end="\n\n")
        assert False


atheris.Setup(sys.argv, fuzz_one_input)
atheris.Fuzz()
