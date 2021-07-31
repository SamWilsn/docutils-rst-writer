from textwrap import dedent
from typing import List, Optional, Tuple

import pytest
from docutils import nodes
from docutils.core import publish_string
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


rewrite_testdata: List[Tuple[str, ...]] = [
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
        "fmt_emphasis",
        """
        *emphasis*
        """,
    ),
    (
        "fmt_strong",
        """
        **strong**
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
    (
        "escape_literal_backslash",
        """
        ``\\``
        """,
    ),
    (
        "escape_backslash",
        """
        \\*escaped*
        """,
    ),
    (
        "escape_backtick",
        """
        ``*``
        """,
    ),
    (
        "escape_bar",
        """
        \\|
        """,
    ),
    (
        "escape_backslash_bar",
        """
        \\\\|
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
        *  a bullet point
        """,
    ),
    (
        "bulleted_lists",
        """
        *  a bullet point using "*"

           -  a sub-list using "-"

              +  yet another sub-list

           -  another item
        """,
    ),
    (
        "definition_lists",
        """
        what
           Definition lists associate a term with a definition.

        *how*
           The term is a one-line phrase, and the definition is one or more
           paragraphs or body elements, indented relative to the term. Blank
           lines are not allowed between term and definition.
        """,
    ),
    #
    # Preformatting
    #
    (
        "preformat",
        """
        An example::

            Whitespace, newlines, blank lines, and all kinds of markup
              (like *this* or \\this) is preserved by literal blocks.
          Lookie here, I've dropped an indentation level
          (but not far enough)

        no more example
        """,
    ),
    (
        "preformat_trim",
        """
        ::

            This is preformatted text, and the
            last "::" paragraph is removed
        """,
    ),
    #
    # Sections
    #
    (
        "sections",
        """
        Chapter 1 Title
        ===============

        Section 1.1 Title
        -----------------

        Subsection 1.1.1 Title
        ~~~~~~~~~~~~~~~~~~~~~~

        Section 1.2 Title
        -----------------

        Chapter 2 Title
        ===============
        """,
    ),
    (
        "subtitle",
        """
        ================
         Document Title
        ================
        ----------
         Subtitle
        ----------

        Section Title
        =============
        """,
    ),
    #
    # Images
    #
    (
        "image",
        """
        .. image:: images/biohazard.png
           :name: banana
           :class: foo bar
           :alt: alternate text
           :height: 100
           :width: 200
           :scale: 50
        """,
    ),
    (
        "image_with_name_with_space",
        """
        .. image:: images/biohazard.png
           :name: banana bobana
        """,
    ),
    (
        "image_with_name",
        """
        .. image:: images/biohazard.png
           :name: banana
        """,
    ),
    (
        "image_with_target_name",
        """
        .. image:: images/biohazard.png
           :target: `banana`_

        .. _banana: http://example.com/banana
        """,
    ),
    (
        "image_with_target_uri",
        """
        .. image:: images/biohazard.png
           :target: http://example.com/image
        """,
    ),
    #
    # References
    #
    (
        "reference_named",
        """
        Banana_

        .. _Banana: http://example.com/banana
        """,
    ),
    (
        "reference_named_phrase_with_backslash",
        """
        `some \\`reference`_
        `another :reference`_

        .. _some `reference: another \\:reference
        .. _another \\:reference: http://example.com/colon
        """,
    ),
    (
        "reference_named_phrase",
        """
        `some reference`_

        .. _some reference: http://example.com
        """,
    ),
    (
        "reference_anonymous",
        """
        anon__

        __ http://example.com
        """,
    ),
    (
        "reference_inline",
        """
        `link to something`_

        _`link to something`
        """,
    ),
    (
        "reference_footnote",
        """
        footnote reference [1]_

        .. [1] some footnote
        """,
    ),
    (
        "reference_footnotes",
        """
        Footnote references, like [5]_.
        Note that footnotes may get
        rearranged, e.g., to the bottom of
        the "page".

        .. [5] A numerical footnote. Note
           there's no colon after the ``]``.
        """,
    ),
    (
        "reference_footnotes_autonumber",
        """
        Autonumbered footnotes are
        possible, like using [#]_ and [#]_.

        .. [#] This is the first one.
        .. [#] This is the second one.

        They may be assigned 'autonumber
        labels' - for instance,
        [#fourth]_ and [#third]_.

        .. [#third] a.k.a. third_

        .. [#fourth] a.k.a. fourth_
        """,
    ),
    (
        "reference_footnotes_autosymbol",
        """
        Auto-symbol footnotes are also
        possible, like this: [*]_ and [*]_.

        .. [*] This is the first one.
        .. [*] This is the second one.
        """,
    ),
    (
        "reference_footnote_with_list",
        """
        footnote reference [1]_

        .. [1] some footnote

           1. hello world

           2. banana
        """,
    ),
    #
    # Substitutions
    #
    (
        "substitution_image",
        """
        The |biohazard| symbol must be used on containers used to dispose of
        medical waste.

        .. |biohazard| image:: biohazard.png
        """,
    ),
    (
        "substitution_replace",
        """
        The |biohazard| symbol must be used on containers used to dispose of
        medical waste.

        .. |biohazard| replace:: here's the *real* |realbiohazard|
        .. |realbiohazard| image:: biohazard.png
        """,
    ),
    (
        "substitution_newline",
        """
        all rights |hello| reserved.

        .. |hello| replace:: BogusMegaCorp
           hello
        """,
    ),
    (
        "substitution_unicode",
        """
        Copyright |copy| 2003, |BogusMegaCorp (TM)| |---|
        all rights reserved.

        .. |copy| unicode:: 0xA9
        .. |BogusMegaCorp (TM)| unicode:: BogusMegaCorp U+2122
        .. |---| unicode:: U+02014
           :trim:
        """,
    ),
    (
        "substitution_unicode_newline",
        """
        all rights |hello| reserved.

        .. |hello| unicode:: BogusMegaCorp
           hello
           :trim:
        """,
    ),
    (
        "substitution_unicode_within_unicode",
        # This should render the literal text `U+1F63F`. If it renders a crying
        # cat face emoji, there's a bug.
        """
        Banana |foo|.

        .. |foo| unicode:: U+0055 +1F63F
           :trim:
        """,
    ),
    (
        "substitution_unicode_double_substitution_with_space",
        "trees seem to match, but the string representations don't",
        """
        .. |boom| unicode:: |baby| |baby|
        .. |baby| replace:: orange

        ka |boom|.
        """,
    ),
    (
        "substitution_unicode_double_substitution",
        """
        .. |boom| unicode:: |baby||baby|
        .. |baby| replace:: orange

        ka |boom|.
        """,
    ),
    (
        "substitution_escaped_substitution",
        """
        .. |boom| replace:: \\|baby|
        .. |baby| replace:: orange

        ka |boom|.
        """,
    ),
    (
        "substitution_unicode_substitution",
        """
        .. |boom| unicode:: |baby|
        .. |baby| replace:: orange

        ka |boom|.
        """,
    ),
    (
        "substitution_unicode_escape",
        """
        .. |boom| unicode:: boom\\ baby

        ka |boom|.
        """,
    ),
    (
        "substitution_trim_as_text",
        """
        .. |boom| replace:: boom
           :trim:

        ka |boom|.
        """,
    ),
    (
        "substitution_unicode_trim",
        """
        .. |boom| unicode:: boom
           :trim:

        ka |boom|.
        """,
    ),
    (
        "substitution_date_time",
        """
        .. |date| date::
        .. |time| date:: %H:%M

        Today's date is |date|.

        This document was generated on |date| at |time|.
        """,
    ),
    #
    # Admonitions
    #
    (
        "admonition_danger",
        """
        .. DANGER::
           Beware killer rabbits!
        """,
    ),
    (
        "admonition_note",
        """
        .. note::
           Beware killer rabbits!
        """,
    ),
    (
        "admonition_with_list",
        """
        .. note:: This is a note admonition.
           This is the second line of the first paragraph.

           - The note contains all indented body elements
             following.
           - It includes this bullet list.
        """,
    ),
]


@pytest.mark.parametrize(
    "src,skip",
    [(x[1], None) if len(x) == 2 else (x[2], x[1]) for x in rewrite_testdata],
    ids=[test[0] for test in rewrite_testdata],
)
def test_rewrite(src: str, skip: Optional[str]) -> None:
    if skip is not None:
        pytest.skip(skip)

    src = dedent(src).lstrip()

    doc = parse_rst(src)
    wrote = write_rst(doc)
    assert wrote is not None

    print("expected doc:\n")
    print(doc, end="\n\n")

    print("actual doc:\n")
    print(parse_rst(wrote), end="\n\n")

    print("original rst:\n")
    print(src)

    print("actual rst:\n")
    print(wrote)
    assert publish_string(wrote).decode("utf-8") == publish_string(src).decode(
        "utf-8"
    )
