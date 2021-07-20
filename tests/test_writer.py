from textwrap import dedent
from typing import Optional

import pytest
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


rewrite_testdata = [
    (
        "paragraphs_and_blockquotes",
        """
        This is a paragraph.  It's quite short.

           This paragraph will result in an indented block of text, typically
           used for quoting other text.

        This is another one.
        """,
    ),
    #
    # Text Formatting
    #
    (
        "fmt_italics",
        """
        *italics*
        """,
    ),
    (
        "fmt_bold",
        """
        **bold**
        """,
    ),
    (
        "fmt_double_back_quotes",
        """
        ``*double* back-quotes``
        """,
    ),
    #
    # Escaping
    #
    # (
    #     "escape_backslash",
    #     """
    #     \\*escaped*
    #     """,
    # ),
    (
        "escape_backtick",
        """
        ``*``
        """,
    ),
    #
    # Lists
    #
    (
        "enumerated_list_arabic",
        """
        1. numbers

        2. numbers
        """,
    ),
    (
        "enumerated_list_alpha_lower",
        """
        a. lowercase

        b. lowercase
        """,
    ),
    (
        "enumerated_list_roman_lower",
        """
        i. lowercase roman

        ii. lowercase roman
        """,
    ),
    (
        "enumerated_list_roman_upper",
        """
        I. uppercase roman

        II. uppercase roman
        """,
    ),
    (
        "enumerated_list_nested",
        """
        1. Outer list part one

           a. Inner list part one

           b. Inner list part two

        2. Outer list part two
        """,
    ),
    (
        "enumerated_lists",
        """
        1. numbers

        A. upper-case letters and it goes over many lines

           with two paragraphs and all!

        a. lower-case letters

           1. with a sub-list

           2. make sure the numbers are in the correct sequence though!

        I. upper-case roman numerals

        i. lower-case roman numerals

        (1) numbers again

        1) and again
        """,
    ),
    (
        "bulleted_list_asterix",
        """
        * a bullet point
        """,
    ),
    (
        "bulleted_lists",
        """
        * a bullet point using "*"

          - a sub-list using "-"

            + yet another sub-list

          - another item
        """,
    ),
]


@pytest.mark.parametrize(
    "src",
    [x for (_, x) in rewrite_testdata],
    ids=[name for (name, _) in rewrite_testdata],
)
def test_rewrite(src: str) -> None:
    src = dedent(src).lstrip()

    doc = parse_rst(src)
    wrote = write_rst(doc)
    assert src == wrote
