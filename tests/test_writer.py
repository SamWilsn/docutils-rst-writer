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
    (
        "fuzz_0001",
        "\xa7:;::\x8a\x9c\xd3",
    ),
    (
        "title_reference",
        """
        :title-reference:`foo`
        """,
    ),
    (
        "transition",
        """
        Paragraph 1.

        ----

        Paragraph 2.
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
        "enumerated_list_arabic_automatic",
        """
        1. numbers

        #. numbers

        #. numbers
        """,
    ),
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
        "enumerated_list_empty_then_paragraph",
        """
        1.

        D
        """,
    ),
    (
        "bulleted_list_asterix",
        """
        *  a bullet point
        """,
    ),
    (
        "bulleted_list_empty",
        """
        *
        *
        """,
    ),
    (
        "bulleted_list_empty_then_paragraph",
        """
        *

        D
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

        After paragraph
        """,
    ),
    (
        "field_lists",
        """
        :Authors:
            Tony J. (Tibs) Ibbs,
            David Goodger

            (and sundry other good-natured folks)

        :Version: 1.0 of 2001/08/08
        :Dedication: To my father.

        After paragraph
        """,
    ),
    (
        "field_list_rcs_keywords",
        """
        :Status: $keyword: expansion text $
        """,
    ),
    (
        "option_lists",
        """
        -a            command-line option "a"
        -b file       options can have arguments
                      and long descriptions
        --long        options can be long also
        --input=file  long options can also have
                      arguments
        /V            DOS/VMS-style options too
        """,
    ),
    (
        "option_lists_group",
        """
        -a            command-line option "a"
        -1 file, --one=file, --two file
                      Multiple options with arguments.
        """,
    ),
    (
        "option_lists_paragraphs",
        """
        -a         Output all.
        -b         Output both (this description is
                   quite long).
        -c arg     Output just arg.
        --long     Output all day long.

        -p         This option has two paragraphs in the description.
                   This is the first.

                   This is the second.  Blank lines may be omitted between
                   options (as above) or left in (as here and below).

        --very-long-option  A VMS-style option.  Note the adjustment for
                            the required two spaces.

        --an-even-longer-option
                   The description can also start on the next line.

        -2, --two  This option has two variants.

        -f FILE, --file=FILE  These two options are synonyms; both have
                              arguments.

        /V         A VMS/DOS-style option.

        after paragraph
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

        After paragraph.
        """,
    ),
    (
        "preformat_per_line",
        """
        Per-line quoting can also be used on
        unindented literal blocks::

        > Useful for quotes from email and
        > for Haskell literate programming.

        After paragraph.
        """,
    ),
    (
        "preformat_line_blocks",
        """
        | Line blocks are useful for addresses,
        | verse, and adornment-free lists.
        |
        | Each new line begins with a
        | vertical bar ("|").
        |     Line breaks and initial indents
        |     are preserved.
        | Continuation lines are wrapped
          portions of long lines; they begin
          with spaces in place of vertical bars.

        After paragraph.
        """,
    ),
    (
        "preformat_doctest",
        """
        Doctest blocks are interactive
        Python sessions. They begin with
        "``>>>``" and end with a blank line.

        >>> print "This is a doctest block."
        This is a doctest block.

        After paragraph.
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
    (
        "reference_citation",
        """
        citation reference [CIT2002]_

        .. [CIT2002] A citation
        """,
    ),
    (
        "reference_citations",
        """
        Citation references, like [CIT2002]_.
        Note that citations may get
        rearranged, e.g., to the bottom of
        the "page".

        .. [CIT2002] A citation
           (as often used in journals).

        Citation labels contain alphanumerics,
        underlines, hyphens and fullstops.
        Case is not significant.

        Given a citation like [this]_, one
        can also refer to it like this_.

        .. [this] here.
        """,
    ),
    (
        "reference_hyperlink",
        """
        https://example.com
        """,
    ),
    (
        "reference_hyperlink_embedded",
        "broken",
        """
        External hyperlinks, like `Python
        <http://www.python.org/>`_.
        """,
    ),
    (
        "reference_internal",
        """
        Internal crossreferences, like example_.

        .. _example:

        This is an example crossreference target.
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
    (
        "substitution_escape",
        "broken [fuzz]",
        """
        |-|*|
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
    #
    # Comments
    #
    (
        "comment_comments",
        """
        .. This text will not be shown
           (but, for instance, in HTML might be
           rendered as an HTML comment)

        After Comment
        """,
    ),
    (
        "comment_empty",
        """
        An "empty comment" does not
        consume following blocks.
        (An empty comment is ".." with
        blank lines before and after.)

        ..

           So this block is not "lost",
           despite its indentation.
        """,
    ),
    (
        "table_grid",
        """
        Grid table:

        +------------+------------+-----------+
        | Header 1   | Header 2   | Header 3  |
        +============+============+===========+
        | body row 1 | column 2   | column 3  |
        +------------+------------+-----------+
        | body row 2 | Cells may span columns.|
        +------------+------------+-----------+
        | body row 3 | Cells may  | - Cells   |
        +------------+ span rows. | - contain |
        | body row 4 |            | - blocks. |
        +------------+------------+-----------+

        After paragraph
        """,
    ),
    (
        "table_simple",
        """
        Simple table:

        =====  =====  ======
           Inputs     Output
        ------------  ------
          A      B    A or B
        =====  =====  ======
        False  False  False
        True   False  True
        False  True   True
        True   True   True
        =====  =====  ======

        After paragraph
        """,
    ),
    (
        "table_with_substitution",
        """
        +--------+--------+--------+
        | |subs| | Cell 2 | Cell 3 |
        +--------+--------+--------+

        .. |subs| image:: biohazard.png
        """,
    ),
    (
        "table_nested",
        """
        +----------------+--------+--------+
        | +----+----+    |        |        |
        | |subs| C0 |    | Cell 2 | Cell 3 |
        | +----+----+    |        |        |
        +----------------+--------+--------+
        """,
    ),
    (
        "table_grid_no_header",
        """
        +--------+--------+--------+
        | Cell 1 | Cell 2 | Cell 3 |
        +--------+--------+--------+
        """,
    ),
    (
        "table_grid_rowspan_then_colspan",
        """
        +------------+------------+-----------+
        | Header 1   | Header 2   | Header 3  |
        +============+============+===========+
        | body row 1 | Cells may span columns.|
        |            +------------+-----------+
        |            | R2C2       | R2C3      |
        +------------+------------+-----------+
        """,
    ),
    (
        "table_grid_rowspan",
        """
        +------------+------------+-----------+
        | Header 1   | Header 2   | Header 3  |
        +============+============+===========+
        | body row 1 | column 2   | column 3  |
        |            +------------+-----------+
        |            | Cells may span columns.|
        +------------+------------------------+
        """,
    ),
    (
        "table_grid_colspan_then_rowspan",
        """
        +------------+------------+-----------+
        | R0C0       | R0C1       | R0C2      |
        +============+============+===========+
        | R1C0C1                  | R1R2C2    |
        +------------+------------+           |
        | R2C0       | R2C1       |           |
        +------------+------------+-----------+
        """,
    ),
    (
        "table_grid_colspan",
        """
        +------------+------------+-----------+
        | Header 1   | Header 2   | Header 3  |
        +============+============+===========+
        | body row 1 | column 2   | column 3  |
        +------------+------------+           |
        | body row 2   column 2   |           |
        +-------------------------+-----------+
        """,
    ),
    (
        "table_grid_rowcolspan",
        """
        +------------+------------+-----------+
        | Header 1   | Header 2   | Header 3  |
        +============+============+===========+
        | body row 1 | column 2     column 3  |
        +------------+                        |
        | body row 2 |                        |
        +------------+------------------------+
        """,
    ),
    (
        "table_grid_rowcolspan_flip",
        """
        +------------+------------+-----------+
        | Header 1   | Header 2   | Header 3  |
        +============+============+===========+
        | column 1     column 2   | column 3  |
        |                         +-----------+
        |                         | row 2     |
        +-------------------------+-----------+
        """,
    ),
    (
        "table_grid_rowspan_bricks",
        """
        +------------+------------------------+
        | R0C0       | R0C1C2                 |
        +============+============+===========+
        | R1C0C1                  | R1C1C2    |
        +------------+------------+-----------+
        | R2C0       | R2C1C2                 |
        +------------+------------------------+
        """,
    ),
    (
        "table_grid_rowspan_bricks_flip",
        """
        +-------------------------+-----------+
        | R0C0C1                  | R0C2      |
        +============+============+===========+
        | R1C0       | R1C1C2                 |
        +------------+------------+-----------+
        | R2C0C1                  | R2C2      |
        +-------------------------+-----------+
        """,
    ),
    (
        "table_css",
        """
        .. csv-table:: Frozen Delights!
           :header: "Treat", "Quantity", "Description"

           "Albatross", 2.99, "On a stick!"
           "Crunchy Frog", 1.49, "If we took the bones"
           "Gannet Ripple", 1.99, "On a stick!"
        """,
    ),
    (
        "table_css_stub",
        "not implemented yet",
        """
        .. csv-table:: Frozen Delights!
           :header: "Treat", "Quantity", "Description"
           :stub-columns: 1

           "Albatross", 2.99, "On a stick!"
           "Crunchy Frog", 1.49, "If we took the bones"
           "Gannet Ripple", 1.99, "On a stick!"
        """,
    ),
    (
        "table_css_wide",
        "colwidth incorrectly calculated",
        """
        .. csv-table:: Frozen Delights!
           :header: "Treat", "Quantity", "Description"
           :stub-columns: 1

           "Albatross", 2.99, "On a stick!"
           "Crunchy Frog", 1.49, "If we took the bones out, it wouldn't be
           crunchy, now would it?"
           "Gannet Ripple", 1.99, "On a stick!"
        """,
    ),
    (
        "table_css_with_widths",
        "not implemented yet",
        """
        .. csv-table:: Frozen Delights!
           :header: "Treat", "Quantity", "Description"
           :widths: 15, 10, 30
           :stub-columns: 1

           "Albatross", 2.99, "On a stick!"
           "Crunchy Frog", 1.49, "If we took the bones out, it wouldn't be
           crunchy, now would it?"
           "Gannet Ripple", 1.99, "On a stick!"
        """,
    ),
    (
        "table_list",
        """
        .. list-table:: *Frozen* Delights!
           :header-rows: 1

           * - Treat
             - Quantity
             - Description
           * - Albatross
             - 2.99
             - On a stick!
           * - Crunchy Frog
             - 1.49
             - If we took the bones out
           * - Gannet Ripple
             - 1.99
             - On a stick!
        """,
    ),
    (
        "table_list_wide",
        "colwidth incorrectly calculated",
        """
        .. list-table:: *Frozen* Delights!
           :header-rows: 1

           * - Treat
             - Quantity
             - Description
           * - Albatross
             - 2.99
             - On a stick!
           * - Crunchy Frog
             - 1.49
             - If we took the bones out, it wouldn't be
               crunchy, now would it?
           * - Gannet Ripple
             - 1.99
             - On a stick!
        """,
    ),
    (
        "table_list_with_widths",
        "not implemented yet",
        """
        .. list-table:: *Frozen* Delights!
           :widths: 15 10 30
           :header-rows: 1

           * - Treat
             - Quantity
             - Description
           * - Albatross
             - 2.99
             - On a stick!
           * - Crunchy Frog
             - 1.49
             - If we took the bones out, it wouldn't be
               crunchy, now would it?
           * - Gannet Ripple
             - 1.99
             - On a stick!
        """,
    ),
    (
        "table_list_only_header",
        """
        .. list-table:: Only Header!
           :header-rows: 1

           * - Treat
           * - Albatross
           * - Crunchy Frog
           * - Gannet Ripple
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
    print("expected doc:\n")
    print(doc, end="\n\n")

    wrote = write_rst(doc)
    assert wrote is not None

    print("actual doc:\n")
    print(parse_rst(wrote), end="\n\n")

    print("original rst:\n")
    print(src)

    print("actual rst:\n")
    print(wrote)
    assert publish_string(wrote).decode("utf-8") == publish_string(src).decode(
        "utf-8"
    )
