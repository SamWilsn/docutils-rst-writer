from textwrap import dedent
from typing import Optional

from docutils import nodes
from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser
from docutils.utils import new_document

from docutils_rst_writer import Writer


def parse_rst(text: str) -> nodes.document:
    parser = Parser()
    components = (Parser,)
    settings = OptionParser(components=components).get_default_values()
    document = new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


def write_rst(doc: nodes.document) -> Optional[str]:
    writer = Writer()
    writer.document = doc
    writer.translate()
    return writer.output


def test_rewrite_paragraph() -> None:
    src = """
    This is a paragraph.  It's quite short.

       This paragraph will result in an indented block of text, typically
       used for quoting other text.

    This is another one.
    """

    src = dedent(src).lstrip()

    doc = parse_rst(src)
    wrote = write_rst(doc)
    assert src == wrote
