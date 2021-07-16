# -*- coding: utf-8 -*-
"""
    sphinxcontrib.writers.rst
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Custom docutils writer for ReStructuredText.

    :copyright: Copyright 2021 by Sam Wilson.
    :license: BSD, see LICENSE.rst for details.

    Based on sphinxcontrib-restbuilder, copyright 2012-2021 by Freek Dijkstra
        and contributors.
    Based on sphinx.writers.text.TextWriter, copyright 2007-2014 by the Sphinx
        team.
"""

from __future__ import absolute_import, print_function, unicode_literals

import logging
import os
import sys
import textwrap
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from docutils import nodes, writers
from docutils.nodes import Node
from docutils.nodes import document as Document
from docutils.nodes import fully_normalize_name

MAXWIDTH = 70
STDINDENT = 3


def _(text: str) -> str:
    return text


def escape_uri(uri: str) -> str:
    if uri.endswith("_"):
        uri = uri[:-1] + "\\_"
    return uri


admonitionlabels = {
    "attention": _("Attention"),
    "caution": _("Caution"),
    "danger": _("Danger"),
    "error": _("Error"),
    "hint": _("Hint"),
    "important": _("Important"),
    "note": _("Note"),
    "seealso": _("See also"),
    "tip": _("Tip"),
    "warning": _("Warning"),
}


class Writer(writers.Writer):
    supported = ("text",)
    settings_spec = ("No options here.", "", ())
    settings_defaults: Dict[Any, Any] = {}

    output: Optional[str] = None

    def __init__(self) -> None:
        super().__init__()

    def translate(self) -> None:
        visitor = RstTranslator(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.body


class RstTranslator(nodes.NodeVisitor):
    nl: str
    sectionchars: str
    states: List[List]
    list_counter: List[int]
    list_formatter: List[Callable[[int], str]]
    sectionlevel: int
    table: Optional[List[Any]]
    body: str

    def __init__(self, document: Document) -> None:
        super().__init__(document)

        self.document = document

        self.nl = os.linesep
        self.sectionchars = '*=-~"+`'
        self.states = [[]]
        self.stateindent = [0]
        self.list_counter = []
        self.list_formatter = []
        self.sectionlevel = 0
        self.table = None
        self.indent = STDINDENT
        self.wrapper = textwrap.TextWrapper(
            width=MAXWIDTH, break_long_words=False, break_on_hyphens=False
        )
        self.body = ""

    def log_warning(self, message: str) -> None:
        name = "docutils_rst_writer.writer"
        logger = logging.getLogger(name)
        if len(logger.handlers) == 0:
            # Logging is not yet configured. Configure it.
            logging.basicConfig(
                level=logging.INFO,
                stream=sys.stderr,
                format="%(levelname)-8s %(message)s",
            )
            logger = logging.getLogger(name)
        logger.warning(message)

    def log_unknown(self, kind: str, node: Node) -> None:
        self.log_warning("%s(%s) unsupported formatting" % (kind, node))

    def wrap(self, text: str, width: int = MAXWIDTH) -> List[str]:
        self.wrapper.width = width
        return self.wrapper.wrap(text)

    def add_text(self, text: str) -> None:
        self.states[-1].append((-1, text))

    def new_state(self, indent: int = STDINDENT) -> None:
        self.states.append([])
        self.stateindent.append(indent)

    def end_state(
        self,
        wrap: bool = True,
        end: Optional[List] = [""],
        first: Optional[str] = None,
    ) -> None:
        content = self.states.pop()
        width = max(MAXWIDTH // 3, MAXWIDTH - sum(self.stateindent))
        indent = self.stateindent.pop()
        result: List[Tuple[int, List[str]]] = []
        toformat: List[str] = []

        def do_format() -> None:
            if not toformat:
                return
            if wrap:
                res = self.wrap("".join(toformat), width=width)
            else:
                res = "".join(toformat).splitlines()
            if end:
                res += end
            result.append((indent, res))

        for itemindent, item in content:
            if itemindent == -1:
                toformat.append(item)
            else:
                do_format()
                result.append((indent + itemindent, item))
                toformat = []
        do_format()
        if first is not None and result:
            itemindent, item = result[0]
            if item:
                result.insert(0, (itemindent - indent, [first + item[0]]))
                result[1] = (itemindent, item[1:])
        self.states[-1].extend(result)

    def visit_document(self, node: Node) -> None:
        self.new_state(0)

    def depart_document(self, node: Node) -> None:
        self.end_state()
        self.body = self.nl.join(
            line and (" " * indent + line)
            for indent, lines in self.states[0]
            for line in lines
        )
        # TODO: add header/footer?

    def visit_highlightlang(self, node: Node) -> None:
        raise nodes.SkipNode

    def visit_section(self, node: Node) -> None:
        self._title_char = self.sectionchars[self.sectionlevel]
        self.sectionlevel += 1

    def depart_section(self, node: Node) -> None:
        self.sectionlevel -= 1

    def visit_topic(self, node: Node) -> None:
        self.new_state(0)

    def depart_topic(self, node: Node) -> None:
        self.end_state()

    visit_sidebar = visit_topic
    depart_sidebar = depart_topic

    def visit_rubric(self, node: Node) -> None:
        self.new_state(0)
        self.add_text("-[ ")

    def depart_rubric(self, node: Node) -> None:
        self.add_text(" ]-")
        self.end_state()

    def visit_compound(self, node: Node) -> None:
        # self.log_unknown("compount", node)
        pass

    def depart_compound(self, node: Node) -> None:
        pass

    def visit_glossary(self, node: Node) -> None:
        # self.log_unknown("glossary", node)
        pass

    def depart_glossary(self, node: Node) -> None:
        pass

    def visit_title(self, node: Node) -> None:
        if isinstance(node.parent, nodes.Admonition):
            self.add_text(node.astext() + ": ")
            raise nodes.SkipNode
        self.new_state(0)

    def depart_title(self, node: Node) -> None:
        if isinstance(node.parent, nodes.section):
            char = self._title_char
        else:
            char = "^"
        text = "".join(x[1] for x in self.states.pop() if x[0] == -1)
        self.stateindent.pop()
        self.states[-1].append((0, ["", text, "%s" % (char * len(text)), ""]))

    def visit_subtitle(self, node: Node) -> None:
        # self.log_unknown("subtitle", node)
        pass

    def depart_subtitle(self, node: Node) -> None:
        pass

    def visit_attribution(self, node: Node) -> None:
        self.add_text("-- ")

    def depart_attribution(self, node: Node) -> None:
        pass

    def visit_desc(self, node: Node) -> None:
        self.new_state(0)

    def depart_desc(self, node: Node) -> None:
        self.end_state()

    def visit_desc_signature(self, node: Node) -> None:
        if node.parent["objtype"] in (
            "class",
            "exception",
            "method",
            "function",
        ):
            self.add_text("**")
        else:
            self.add_text("``")

    def depart_desc_signature(self, node: Node) -> None:
        if node.parent["objtype"] in (
            "class",
            "exception",
            "method",
            "function",
        ):
            self.add_text("**")
        else:
            self.add_text("``")

    def visit_desc_name(self, node: Node) -> None:
        # self.log_unknown("desc_name", node)
        pass

    def depart_desc_name(self, node: Node) -> None:
        pass

    def visit_desc_addname(self, node: Node) -> None:
        # self.log_unknown("desc_addname", node)
        pass

    def depart_desc_addname(self, node: Node) -> None:
        pass

    def visit_desc_type(self, node: Node) -> None:
        # self.log_unknown("desc_type", node)
        pass

    def depart_desc_type(self, node: Node) -> None:
        pass

    def visit_desc_returns(self, node: Node) -> None:
        self.add_text(" -> ")

    def depart_desc_returns(self, node: Node) -> None:
        pass

    def visit_desc_parameterlist(self, node: Node) -> None:
        self.add_text("(")
        self.first_param = 1

    def depart_desc_parameterlist(self, node: Node) -> None:
        self.add_text(")")

    def visit_desc_parameter(self, node: Node) -> None:
        if not self.first_param:
            self.add_text(", ")
        else:
            self.first_param = 0
        self.add_text(node.astext())
        raise nodes.SkipNode

    def visit_desc_optional(self, node: Node) -> None:
        self.add_text("[")

    def depart_desc_optional(self, node: Node) -> None:
        self.add_text("]")

    def visit_desc_annotation(self, node: Node) -> None:
        content = node.astext()
        if len(content) > MAXWIDTH:
            h = int(MAXWIDTH / 3)
            content = content[:h] + " ... " + content[-h:]
            self.add_text(content)
            raise nodes.SkipNode

    def depart_desc_annotation(self, node: Node) -> None:
        pass

    def visit_refcount(self, node: Node) -> None:
        pass

    def depart_refcount(self, node: Node) -> None:
        pass

    def visit_desc_content(self, node: Node) -> None:
        self.new_state(self.indent)

    def depart_desc_content(self, node: Node) -> None:
        self.end_state()

    def visit_figure(self, node: Node) -> None:
        self.new_state(self.indent)

    def depart_figure(self, node: Node) -> None:
        self.end_state()

    def visit_caption(self, node: Node) -> None:
        # self.log_unknown("caption", node)
        pass

    def depart_caption(self, node: Node) -> None:
        pass

    def visit_productionlist(self, node: Node) -> None:
        self.new_state(self.indent)
        names = []
        for production in node:
            names.append(production["tokenname"])
        maxlen = max(len(name) for name in names)
        for production in node:
            if production["tokenname"]:
                self.add_text(production["tokenname"].ljust(maxlen) + " ::=")
                lastname = production["tokenname"]
            else:
                self.add_text("%s    " % (" " * len(lastname)))
            self.add_text(production.astext() + self.nl)
        self.end_state(wrap=False)
        raise nodes.SkipNode

    def visit_seealso(self, node: Node) -> None:
        self.new_state(self.indent)

    def depart_seealso(self, node: Node) -> None:
        self.end_state(first="")

    def visit_footnote(self, node: Node) -> None:
        self._footnote = node.children[0].astext().strip()
        self.new_state(len(self._footnote) + self.indent)

    def depart_footnote(self, node: Node) -> None:
        self.end_state(first="[%s] " % self._footnote)

    def visit_citation(self, node: Node) -> None:
        if len(node) and isinstance(node[0], nodes.label):
            self._citlabel = node[0].astext()
        else:
            self._citlabel = ""
        self.new_state(len(self._citlabel) + self.indent)

    def depart_citation(self, node: Node) -> None:
        self.end_state(first="[%s] " % self._citlabel)

    def visit_label(self, node: Node) -> None:
        raise nodes.SkipNode

    # TODO: option list could use some better styling

    def visit_option_list(self, node: Node) -> None:
        # self.log_unknown("option_list", node)
        pass

    def depart_option_list(self, node: Node) -> None:
        pass

    def visit_option_list_item(self, node: Node) -> None:
        self.new_state(0)

    def depart_option_list_item(self, node: Node) -> None:
        self.end_state()

    def visit_option_group(self, node: Node) -> None:
        self._firstoption = True

    def depart_option_group(self, node: Node) -> None:
        self.add_text("     ")

    def visit_option(self, node: Node) -> None:
        if self._firstoption:
            self._firstoption = False
        else:
            self.add_text(", ")

    def depart_option(self, node: Node) -> None:
        pass

    def visit_option_string(self, node: Node) -> None:
        # self.log_unknown("option_string", node)
        pass

    def depart_option_string(self, node: Node) -> None:
        pass

    def visit_option_argument(self, node: Node) -> None:
        self.add_text(node["delimiter"])

    def depart_option_argument(self, node: Node) -> None:
        pass

    def visit_description(self, node: Node) -> None:
        # self.log_unknown("description", node)
        pass

    def depart_description(self, node: Node) -> None:
        pass

    def visit_tabular_col_spec(self, node: Node) -> None:
        raise nodes.SkipNode

    def visit_colspec(self, node: Node) -> None:
        assert self.table is not None
        self.table[0].append(node["colwidth"])
        raise nodes.SkipNode

    def visit_tgroup(self, node: Node) -> None:
        # self.log_unknown("tgroup", node)
        pass

    def depart_tgroup(self, node: Node) -> None:
        pass

    def visit_thead(self, node: Node) -> None:
        # self.log_unknown("thead", node)
        pass

    def depart_thead(self, node: Node) -> None:
        pass

    def visit_tbody(self, node: Node) -> None:
        assert self.table is not None
        self.table.append("sep")

    def depart_tbody(self, node: Node) -> None:
        pass

    def visit_row(self, node: Node) -> None:
        assert self.table is not None
        self.table.append([])

    def depart_row(self, node: Node) -> None:
        pass

    def visit_entry(self, node: Node) -> None:
        if "morerows" in node or "morecols" in node:
            self.log_warning(
                "Column or row spanning cells are not implemented."
            )
        self.new_state(0)

    def depart_entry(self, node: Node) -> None:
        assert self.table is not None
        text = self.nl.join(self.nl.join(x[1]) for x in self.states.pop())
        self.stateindent.pop()
        self.table[-1].append(text)

    def visit_table(self, node: Node) -> None:
        if self.table:
            self.log_warning("Nested tables are not supported.")
        self.new_state(0)
        self.table = [[]]

    def depart_table(self, node: Node) -> None:
        assert self.table is not None
        lines = self.table[1:]
        fmted_rows: List[List[List[str]]] = []
        colwidths = self.table[0]
        realwidths = colwidths[:]
        separator = 0
        # don't allow paragraphs in table cells for now
        for line in lines:
            if line == "sep":
                separator = len(fmted_rows)
            else:
                cells = []
                for i, cell in enumerate(line):
                    par = self.wrap(cell, width=colwidths[i])
                    if par:
                        maxwidth = max(list(map(len, par)))
                    else:
                        maxwidth = 0
                    realwidths[i] = max(realwidths[i], maxwidth)
                    cells.append(par)
                fmted_rows.append(cells)

        def writesep(char: str = "-") -> None:
            out = ["+"]
            for width in realwidths:
                out.append(char * (width + 2))
                out.append("+")
            self.add_text("".join(out) + self.nl)

        def writerow(row: Sequence) -> None:
            lines = list(zip(*row))
            for line in lines:
                out = ["|"]
                for i, cell in enumerate(line):
                    if cell:
                        out.append(" " + cell.ljust(realwidths[i] + 1))
                    else:
                        out.append(" " * (realwidths[i] + 2))
                    out.append("|")
                self.add_text("".join(out) + self.nl)

        for i, row in enumerate(fmted_rows):
            if separator and i == separator:
                writesep("=")
            else:
                writesep("-")
            writerow(row)
        writesep("-")
        self.table = None
        self.end_state(wrap=False)

    def visit_acks(self, node: Node) -> None:
        self.new_state(0)
        self.add_text(
            ", ".join(n.astext() for n in node.children[0].children) + "."
        )
        self.end_state()
        raise nodes.SkipNode

    def visit_image(self, node: Node) -> None:
        self.new_state(0)
        if "uri" in node:
            self.add_text(_(".. image:: %s") % escape_uri(node["uri"]))
        elif "target" in node.attributes:
            self.add_text(_(".. image: %s") % node["target"])
        elif "alt" in node.attributes:
            self.add_text(_("[image: %s]") % node["alt"])
        else:
            self.add_text(_("[image]"))
        self.end_state(wrap=False)
        raise nodes.SkipNode

    def visit_transition(self, node: Node) -> None:
        indent = sum(self.stateindent)
        self.new_state(0)
        self.add_text("=" * (MAXWIDTH - indent))
        self.end_state()
        raise nodes.SkipNode

    def visit_bullet_list(self, node: Node) -> None:
        def bullet_list_format(counter: int) -> str:
            return "*"

        self.list_counter.append(-1)  # TODO: just 0 is fine.
        self.list_formatter.append(bullet_list_format)

    def depart_bullet_list(self, node: Node) -> None:
        self.list_counter.pop()
        self.list_formatter.pop()

    def visit_enumerated_list(self, node: Node) -> None:
        def enumerated_list_format(counter: int) -> str:
            return str(counter) + "."

        self.list_counter.append(0)
        self.list_formatter.append(enumerated_list_format)

    def depart_enumerated_list(self, node: Node) -> None:
        self.list_counter.pop()
        self.list_formatter.pop()

    def visit_list_item(self, node: Node) -> None:
        self.list_counter[-1] += 1
        bullet_formatter = self.list_formatter[-1]
        bullet = bullet_formatter(self.list_counter[-1])
        indent = max(self.indent, len(bullet) + 1)
        self.new_state(indent)

    def depart_list_item(self, node: Node) -> None:
        # formatting to make the string `self.stateindent[-1]` chars long.
        format = "%%-%ds" % (self.stateindent[-1])
        bullet_formatter = self.list_formatter[-1]
        bullet = format % bullet_formatter(self.list_counter[-1])
        self.end_state(first=bullet, end=None)

    def visit_definition_list(self, node: Node) -> None:
        pass

    def depart_definition_list(self, node: Node) -> None:
        pass

    def visit_definition_list_item(self, node: Node) -> None:
        self._li_has_classifier = len(node) >= 2 and isinstance(
            node[1], nodes.classifier
        )

    def depart_definition_list_item(self, node: Node) -> None:
        pass

    def visit_term(self, node: Node) -> None:
        self.new_state(0)

    def depart_term(self, node: Node) -> None:
        if not self._li_has_classifier:
            self.end_state(end=None)

    def visit_termsep(self, node: Node) -> None:
        self.add_text(", ")
        raise nodes.SkipNode

    def visit_classifier(self, node: Node) -> None:
        self.add_text(" : ")

    def depart_classifier(self, node: Node) -> None:
        self.end_state(end=None)

    def visit_definition(self, node: Node) -> None:
        self.new_state(self.indent)

    def depart_definition(self, node: Node) -> None:
        self.end_state()

    def visit_field_list(self, node: Node) -> None:
        # self.log_unknown("field_list", node)
        pass

    def depart_field_list(self, node: Node) -> None:
        pass

    def visit_field(self, node: Node) -> None:
        self.new_state(0)

    def depart_field(self, node: Node) -> None:
        self.end_state(end=None)

    def visit_field_name(self, node: Node) -> None:
        self.add_text(":")

    def depart_field_name(self, node: Node) -> None:
        self.add_text(":")
        content = node.astext()
        self.add_text((16 - len(content)) * " ")

    def visit_field_body(self, node: Node) -> None:
        self.new_state(self.indent)

    def depart_field_body(self, node: Node) -> None:
        self.end_state()

    def visit_centered(self, node: Node) -> None:
        pass

    def depart_centered(self, node: Node) -> None:
        pass

    def visit_hlist(self, node: Node) -> None:
        # self.log_unknown("hlist", node)
        pass

    def depart_hlist(self, node: Node) -> None:
        pass

    def visit_hlistcol(self, node: Node) -> None:
        # self.log_unknown("hlistcol", node)
        pass

    def depart_hlistcol(self, node: Node) -> None:
        pass

    def visit_admonition(self, node: Node) -> None:
        self.new_state(0)

    def depart_admonition(self, node: Node) -> None:
        self.end_state()

    def _visit_admonition(self, node: Node) -> None:
        self.new_state(self.indent)

    def _make_depart_admonition(
        name: str,
    ) -> Callable[["RstTranslator", Node], None]:
        def depart_admonition(self: "RstTranslator", node: Node) -> None:
            self.end_state(first=admonitionlabels[name] + ": ")

        return depart_admonition

    visit_attention = _visit_admonition
    depart_attention = _make_depart_admonition("attention")
    visit_caution = _visit_admonition
    depart_caution = _make_depart_admonition("caution")
    visit_danger = _visit_admonition
    depart_danger = _make_depart_admonition("danger")
    visit_error = _visit_admonition
    depart_error = _make_depart_admonition("error")
    visit_hint = _visit_admonition
    depart_hint = _make_depart_admonition("hint")
    visit_important = _visit_admonition
    depart_important = _make_depart_admonition("important")
    visit_note = _visit_admonition
    depart_note = _make_depart_admonition("note")
    visit_tip = _visit_admonition
    depart_tip = _make_depart_admonition("tip")
    visit_warning = _visit_admonition
    depart_warning = _make_depart_admonition("warning")

    def visit_versionmodified(self, node: Node) -> None:
        self.new_state(0)

    def depart_versionmodified(self, node: Node) -> None:
        self.end_state()

    def visit_literal_block(self, node: Node) -> None:
        is_code_block = False
        # Support for Sphinx < 2.0, which defines classes['code', 'language']
        if "code" in node.get("classes", []):
            is_code_block = True
            if (
                node.get("language", "default") == "default"
                and len(node["classes"]) >= 2
            ):
                node["language"] = node["classes"][1]

        # highlight_args is the only way to distinguish
        # between :: and .. code:: in Sphinx 2 or higher.
        if node.get("highlight_args", None) is not None:
            is_code_block = True
        if is_code_block:
            if node.get("language", "default") == "default":
                directive = ".. code::"
            else:
                directive = ".. code:: %s" % node["language"]
            if node.get("linenos"):
                indent = self.indent * " "
                directive += "%s%s:number-lines:" % (self.nl, indent)
        else:
            directive = "::"
        self.new_state(0)
        self.add_text(directive)
        self.end_state(wrap=False)
        self.new_state(self.indent)

    def depart_literal_block(self, node: Node) -> None:
        self.end_state(wrap=False)

    def visit_doctest_block(self, node: Node) -> None:
        self.new_state(0)

    def depart_doctest_block(self, node: Node) -> None:
        self.end_state(wrap=False)

    def visit_line_block(self, node: Node) -> None:
        self.new_state(0)

    def depart_line_block(self, node: Node) -> None:
        self.end_state(wrap=False)

    def visit_line(self, node: Node) -> None:
        # self.log_unknown("line", node)
        pass

    def depart_line(self, node: Node) -> None:
        pass

    def visit_block_quote(self, node: Node) -> None:
        self.new_state(self.indent)

    def depart_block_quote(self, node: Node) -> None:
        self.end_state()

    def visit_compact_paragraph(self, node: Node) -> None:
        self.visit_paragraph(node)

    def depart_compact_paragraph(self, node: Node) -> None:
        self.depart_paragraph(node)

    def visit_paragraph(self, node: Node) -> None:
        if not isinstance(node.parent, nodes.Admonition):
            self.new_state(0)

    def depart_paragraph(self, node: Node) -> None:
        if not isinstance(node.parent, nodes.Admonition):
            self.end_state()

    def visit_target(self, node: Node) -> None:
        is_inline = node.parent.tagname in ("paragraph",)
        if is_inline or node.get("anonymous"):
            return
        refid = node.get("refid")
        refuri = node.get("refuri")
        if refuri:
            raise NotImplementedError()

        if refid:
            self.new_state(0)
            if node.get("ids"):
                self.add_text(
                    self.nl.join(
                        ".. _%s: %s_" % (id, refid) for id in node["ids"]
                    )
                )
            else:
                self.add_text(".. _" + node["refid"] + ":")
            self.end_state(wrap=False)
        raise nodes.SkipNode

    def depart_target(self, node: Node) -> None:
        pass

    def visit_index(self, node: Node) -> None:
        raise nodes.SkipNode

    def visit_substitution_definition(self, node: Node) -> None:
        raise nodes.SkipNode

    def visit_pending_xref(self, node: Node) -> None:
        pass

    def depart_pending_xref(self, node: Node) -> None:
        pass

    def visit_reference(self, node: Node) -> None:
        refname = node.get("name")
        refbody = node.astext()
        refuri = node.get("refuri")
        refid = node.get("refid")
        if node.get("anonymous"):
            underscore = "__"
        else:
            underscore = "_"
        if not refname:
            refname = refbody

        if refid:
            if refid == self.document.nameids.get(
                fully_normalize_name(refname)
            ):
                self.add_text("`%s`%s" % (refname, underscore))
            else:
                self.add_text("`%s <%s_>`%s" % (refname, refid, underscore))
            raise nodes.SkipNode
        elif refuri:
            if refuri == refname:
                self.add_text(escape_uri(refuri))
            else:
                self.add_text(
                    "`%s <%s>`%s" % (refname, escape_uri(refuri), underscore)
                )
            raise nodes.SkipNode

    def depart_reference(self, node: Node) -> None:
        pass

    def visit_download_reference(self, node: Node) -> None:
        self.log_unknown("download_reference", node)
        pass

    def depart_download_reference(self, node: Node) -> None:
        pass

    def visit_emphasis(self, node: Node) -> None:
        self.add_text("*")

    def depart_emphasis(self, node: Node) -> None:
        self.add_text("*")

    def visit_literal_emphasis(self, node: Node) -> None:
        self.add_text("*")

    def depart_literal_emphasis(self, node: Node) -> None:
        self.add_text("*")

    def visit_strong(self, node: Node) -> None:
        self.add_text("**")

    def depart_strong(self, node: Node) -> None:
        self.add_text("**")

    def visit_abbreviation(self, node: Node) -> None:
        self.add_text("")

    def depart_abbreviation(self, node: Node) -> None:
        if node.hasattr("explanation"):
            self.add_text(" (%s)" % node["explanation"])

    def visit_title_reference(self, node: Node) -> None:
        # self.log_unknown("title_reference", node)
        self.add_text("*")

    def depart_title_reference(self, node: Node) -> None:
        self.add_text("*")

    def visit_literal(self, node: Node) -> None:
        self.add_text("``")

    def depart_literal(self, node: Node) -> None:
        self.add_text("``")

    def visit_subscript(self, node: Node) -> None:
        self.add_text(":sub:`")

    def depart_subscript(self, node: Node) -> None:
        self.add_text("`")

    def visit_superscript(self, node: Node) -> None:
        self.add_text(":sup:`")

    def depart_superscript(self, node: Node) -> None:
        self.add_text("`")

    def visit_footnote_reference(self, node: Node) -> None:
        self.add_text("[%s]" % node.astext())
        raise nodes.SkipNode

    def visit_citation_reference(self, node: Node) -> None:
        self.add_text("[%s]" % node.astext())
        raise nodes.SkipNode

    def visit_math_block(self, node: Node) -> None:
        self.add_text(".. math::")
        self.new_state(self.indent)

    def depart_math_block(self, node: Node) -> None:
        self.end_state(wrap=False)

    def visit_Text(self, node: Node) -> None:
        self.add_text(node.astext())

    def depart_Text(self, node: Node) -> None:
        pass

    def visit_generated(self, node: Node) -> None:
        # self.log_unknown("generated", node)
        pass

    def depart_generated(self, node: Node) -> None:
        pass

    def visit_inline(self, node: Node) -> None:
        pass

    def depart_inline(self, node: Node) -> None:
        pass

    def visit_problematic(self, node: Node) -> None:
        pass

    def depart_problematic(self, node: Node) -> None:
        pass

    def visit_system_message(self, node: Node) -> None:
        self.new_state(0)
        self.add_text("<SYSTEM MESSAGE: %s>" % node.astext())
        self.end_state()
        raise nodes.SkipNode

    def visit_comment(self, node: Node) -> None:
        raise nodes.SkipNode

    def visit_meta(self, node: Node) -> None:
        # only valid for HTML
        raise nodes.SkipNode

    def visit_raw(self, node: Node) -> None:
        if "text" in node.get("format", "").split():
            self.body += node.astext()
        raise nodes.SkipNode

    def visit_docinfo(self, node: Node) -> None:
        raise nodes.SkipNode

    def unknown_visit(self, node: Node) -> None:
        self.log_unknown(node.__class__.__name__, node)

    def unknown_departure(self, node: Node) -> None:
        pass

    default_visit = unknown_visit
