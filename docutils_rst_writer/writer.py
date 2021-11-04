# -*- coding: utf-8 -*-
"""
    docutils-rst-writer
    ~~~~~~~~~~~~~~~~~~~

    Custom docutils writer for ReStructuredText.

    :copyright: Copyright 2021 by Sam Wilson.
    :license: BSD, see LICENSE.rst for details.

    Based on sphinxcontrib-restbuilder, copyright 2012-2021 by Freek Dijkstra
        and contributors.
    Based on sphinx.writers.text.TextWriter, copyright 2007-2014 by the Sphinx
        team.
"""

from __future__ import (
    absolute_import,
    annotations,
    print_function,
    unicode_literals,
)

import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from docutils import nodes, writers
from docutils.nodes import Node
from docutils.nodes import document as Document
from docutils.nodes import fully_normalize_name
from docutils.utils import roman

from .table import CellContent, Table


def escape_uri(uri: str) -> str:
    if uri.endswith("_"):
        uri = uri[:-1] + "\\_"
    return uri


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
        self.output = "\n".join(visitor.lines)


class _ListItem:
    counter: Optional[int]
    bullet: Optional[str]
    prefix: str
    suffix: str
    enumtype: str

    def __init__(self, node: Node):
        parent = node.parent
        self.prefix = parent.get("prefix", "")
        self.counter = None
        self.bullet = None

        if isinstance(parent, nodes.enumerated_list):
            self.enumtype = parent.get("enumtype", "arabic")
            start = parent.get("start", 1)
            self.counter = parent.index(node) + start
            self.suffix = parent.get("suffix", ".")
        elif isinstance(parent, nodes.bullet_list):
            self.enumtype = "bullet"
            self.bullet = parent.get("bullet", "*")
            self.suffix = parent.get("suffix", "")
        else:
            raise NotImplementedError(
                f"lists of type {parent.__class__.__name__}"
            )

    def format(self) -> str:
        if self.counter is None:
            return self._bullet()
        else:
            if self.enumtype == "arabic":
                formatter = self._arabic
            elif self.enumtype == "loweralpha":
                formatter = self._lower_alpha
            elif self.enumtype == "upperalpha":
                formatter = self._upper_alpha
            elif self.enumtype == "lowerroman":
                formatter = self._lower_roman
            elif self.enumtype == "upperroman":
                formatter = self._upper_roman
            else:
                formatter = self._arabic
                RstTranslator.log_warning(
                    f"list format `{self.enumtype}` is unknown, using arabic"
                )

            return formatter(self.counter)

    def _bullet(self) -> str:
        return f"{self.prefix}{self.bullet}{self.suffix}"

    def _upper_alpha(self, counter: int) -> str:
        if counter < 1 or counter > 26:
            raise ValueError(f"list counter ({counter}) is out of range")

        code = ord("A") + counter - 1
        return f"{self.prefix}{chr(code)}{self.suffix}"

    def _lower_alpha(self, counter: int) -> str:
        if counter < 1 or counter > 26:
            raise ValueError(f"list counter ({counter}) is out of range")

        code = ord("a") + counter - 1
        return f"{self.prefix}{chr(code)}{self.suffix}"

    def _lower_roman(self, counter: int) -> str:
        txt = roman.toRoman(counter).lower()
        return f"{self.prefix}{txt}{self.suffix}"

    def _upper_roman(self, counter: int) -> str:
        txt = roman.toRoman(counter)
        return f"{self.prefix}{txt}{self.suffix}"

    def _arabic(self, counter: int) -> str:
        return f"{self.prefix}{counter}{self.suffix}"


@dataclass
class _Reference:
    text_only: bool
    anonymous: bool
    target: Optional[str]
    refname: Optional[str]

    def __init__(self, document: Document, node: Node):
        self.anonymous = "anonymous" in node and bool(node["anonymous"])
        self.target = None

        self.refname = node.get("name", node.get("refname", None))
        refuri = node.get("refuri")
        refid = node.get("refid")

        if self.refname is None:
            refname = node.astext()
        else:
            refname = self.refname

        if refid:
            normalized = fully_normalize_name(refname)
            if refid == document.nameids.get(normalized):
                self.target = refname
            else:
                self.target = refid

            if self.refname is None:
                self.refname = self.target
        elif refuri:
            if refuri == refname:
                self.target = escape_uri(refuri)
            else:
                self.target = escape_uri(refuri)
        elif self.refname:
            self.target = f"`{self.refname}`_"

        self.text_only = all(isinstance(c, nodes.Text) for c in node.children)
        self.image_only = (
            (not self.text_only)
            and len(node.children) == 1
            and isinstance(node.children[0], nodes.image)
        )


@dataclass
class _AttrKind:
    node_attr: str
    rst_attr: str
    flag: bool

    def __init__(
        self,
        node_attr: str,
        rst_attr: Optional[str] = None,
        flag: bool = False,
    ) -> None:
        self.node_attr = node_attr
        self.rst_attr = node_attr if rst_attr is None else rst_attr
        self.flag = flag


@dataclass
class _Capture:
    lines: List[str] = field(default_factory=lambda: [""])
    indent: int = 0
    line_block_indent: int = 0
    section_depth: Optional[int] = None
    table: Optional[Table] = None
    reference_substitutions: List[str] = field(default_factory=list)
    allow_inlines: List[bool] = field(default_factory=lambda: [True])


class RstTranslator(nodes.NodeVisitor):
    captures: List[_Capture]
    title_underline: str = "=-~#_`:.'^*+\""
    reference_substitution_count: int
    extra_substitutions: Dict[str, Tuple[str, Optional[str]]]

    role_count: int
    extra_roles: Dict[Tuple[str, ...], str]

    @property
    def allow_inlines(self) -> List[bool]:
        return self.captures[-1].allow_inlines

    @property
    def reference_substitutions(self) -> List[str]:
        return self.captures[-1].reference_substitutions

    @property
    def lines(self) -> List[str]:
        return self.captures[-1].lines

    @property
    def indent(self) -> int:
        return self.captures[-1].indent

    @indent.setter
    def indent(self, v: int) -> None:
        self.captures[-1].indent = v

    @property
    def line_block_indent(self) -> int:
        return self.captures[-1].line_block_indent

    @line_block_indent.setter
    def line_block_indent(self, v: int) -> None:
        self.captures[-1].line_block_indent = v

    @property
    def section_depth(self) -> Optional[int]:
        return self.captures[-1].section_depth

    @section_depth.setter
    def section_depth(self, v: Optional[int]) -> None:
        self.captures[-1].section_depth = v

    @property
    def table(self) -> Optional[Table]:
        return self.captures[-1].table

    @table.setter
    def table(self, v: Optional[Table]) -> None:
        self.captures[-1].table = v

    def __init__(self, document: Document) -> None:
        super().__init__(document)
        self.captures = [_Capture()]
        self.reference_substitution_count = 0
        self.extra_substitutions = {}

        self.role_count = 0
        self.extra_roles = {}

    @staticmethod
    def log_warning(message: str) -> None:
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

    @classmethod
    def log_unknown(cls, kind: str, node: Node) -> None:
        cls.log_warning("%s(%s) unsupported formatting" % (kind, node))

    def capture(self) -> None:
        self.captures.append(_Capture(section_depth=self.section_depth))

    def release(self) -> _Capture:
        assert len(self.captures) > 1
        return self.captures.pop()

    def write(self, text: str) -> None:
        lines = text.split("\n")
        indent = " " * self.indent

        if not self.lines[-1] and lines[0]:
            lines[0] = indent + lines[0]

        for idx in range(1, len(lines)):
            if lines[idx]:
                lines[idx] = indent + lines[idx]

        self.lines[-1] += lines[0]
        self.lines.extend(lines[1:])

    def write_markup_start(
        self,
        node: Node,
        name: str,
    ) -> None:
        if isinstance(node.parent, nodes.substitution_definition):
            self.write(f"{name}::")
        else:
            # TODO: Should we assert self.lines[-1] is blank here?
            self.write(f".. {name}::")

    def write_attributes(
        self,
        node: Node,
        attrs: Tuple[Union[str, _AttrKind], ...],
    ) -> None:
        wrote_any = False
        if isinstance(node.parent, nodes.reference):
            reference = _Reference(self.document, node.parent)
            if reference.target is not None:
                wrote_any = True
                self.write(f":target: {reference.target}\n")

        for item in attrs:
            wrote_one = False
            if isinstance(item, str):
                kind = _AttrKind(item)
            else:
                kind = item

            node_attr = kind.node_attr
            rst_attr = kind.rst_attr

            if node_attr not in node or not node.is_not_default(node_attr):
                continue

            value: str

            if node_attr == "names":
                if len(node["names"]) > 1:
                    RstTranslator.log_warning("multiple names not supported")

                if len(node["names"]) > 0:
                    value = node["names"][0]
                    wrote_one = True
                    self.write(":name:")

            elif node_attr == "classes":
                value = " ".join(node["classes"])

                if value:
                    wrote_one = True
                    self.write(":class:")

            else:
                value = node[node_attr]

                self.write(f":{rst_attr}:")
                wrote_one = True

            if wrote_one:
                wrote_any = True

                if kind.flag:
                    self.write("\n")
                else:
                    self.write(f" {value}\n")

        if wrote_any:
            self.write("\n\n")
        else:
            self.write("\n")

    def visit_document(self, node: Node) -> None:
        pass

    def depart_document(self, node: Node) -> None:
        if self.extra_substitutions:
            self.write("\n\n")

            for name, (value, dest) in self.extra_substitutions.items():
                self.write(f".. |{name}| replace:: {value}\n")
                if dest is not None:
                    self.write(f".. _{name}: {dest}\n")
                self.write("\n")

        if self.extra_roles:
            self.write("\n\n")

            for classes, name in self.extra_roles.items():
                self.write(f".. role:: {name}\n")
                self.indent += 3
                class_str = " ".join(classes)
                self.write(f":class: {class_str}\n")
                self.indent -= 3
                self.write("\n")

    def visit_paragraph(self, node: Node) -> None:
        pass

    def depart_paragraph(self, node: Node) -> None:
        self.write("\n\n")

    def visit_compound(self, node: Node) -> None:
        self.write(".. compound::\n\n")
        self.indent += 3

    def depart_compound(self, node: Node) -> None:
        self.write("\n\n")
        self.indent -= 3

    def needs_space(self, node: Node) -> bool:
        text = str(node).replace("\x00", "\\")

        if not node.parent or not text or text[0].isspace():
            return False

        index = node.parent.index(node)
        if index == 0:
            return False

        preceding = node.parent.children[index - 1]
        if not isinstance(preceding, node.__class__):
            return False

        preceding_text = str(preceding)
        return bool(preceding_text) and not preceding_text[-1].isspace()

    def visit_Text(self, node: Node) -> None:
        # Escape `|` in text nodes (is an issue in `unicode::` substitutions.)
        text = re.sub("(?<!\x00)\\|", "\x00|", str(node))

        # Docutils converts backslashes into nuls, so we flip them back.
        text = text.replace("\x00", "\\")

        # Insert whitespace between adjacent text nodes (mostly important for
        # substitutions.)
        if self.needs_space(node):
            self.write(" ")

        self.write(text)

    def depart_Text(self, node: Node) -> None:
        pass

    def visit_block_quote(self, node: Node) -> None:
        self.indent += 3

    def depart_block_quote(self, node: Node) -> None:
        self.indent -= 3

    def visit_strong(self, node: Node) -> None:
        self.write("**")

    def depart_strong(self, node: Node) -> None:
        self.write("**")

    def visit_literal(self, node: Node) -> None:
        self.write("``")

    def depart_literal(self, node: Node) -> None:
        self.write("``")

    def visit_emphasis(self, node: Node) -> None:
        self.write("*")

    def depart_emphasis(self, node: Node) -> None:
        self.write("*")

    def visit_definition_list(self, node: Node) -> None:
        pass

    def depart_definition_list(self, node: Node) -> None:
        pass

    def visit_definition_list_item(self, node: Node) -> None:
        pass

    def depart_definition_list_item(self, node: Node) -> None:
        pass

    def visit_term(self, node: Node) -> None:
        pass

    def depart_term(self, node: Node) -> None:
        self.write("\n")

    def visit_definition(self, node: Node) -> None:
        self.indent += 3

    def depart_definition(self, node: Node) -> None:
        self.indent -= 3

    def visit_bullet_list(self, node: Node) -> None:
        pass

    def depart_bullet_list(self, node: Node) -> None:
        self.write("\n")

    def visit_enumerated_list(self, node: Node) -> None:
        pass

    def depart_enumerated_list(self, node: Node) -> None:
        self.write("\n")

    def visit_list_item(self, node: Node) -> None:
        item = _ListItem(node)
        formatted = item.format() + " "
        self.write(formatted)
        self.indent += len(formatted)

    def depart_list_item(self, node: Node) -> None:
        item = _ListItem(node)
        formatted = item.format() + " "
        self.indent -= len(formatted)
        self.write("\n")

    def visit_field_list(self, node: Node) -> None:
        pass  # TODO

    def depart_field_list(self, node: Node) -> None:
        self.write("\n")

    def visit_field(self, node: Node) -> None:
        pass  # TODO

    def depart_field(self, node: Node) -> None:
        pass  # TODO

    def visit_field_name(self, node: Node) -> None:
        self.write(":")

    def depart_field_name(self, node: Node) -> None:
        self.write(": ")

    def visit_field_body(self, node: Node) -> None:
        self.indent += 3

    def depart_field_body(self, node: Node) -> None:
        self.indent -= 3

    def visit_literal_block(
        self,
        node: Node,
        language: Optional[str] = None,
    ) -> None:
        # TODO: Make this more robust
        is_code = "code" in node["classes"]

        if language:
            lang = " " + language
            is_code = True
        elif "python" in node["classes"]:
            lang = " python"
        else:
            lang = ""

        number_lines = "\n"

        if not is_code:
            is_code = not all(isinstance(c, nodes.Text) for c in node.children)

        if isinstance(node.children[0], nodes.inline):
            if "ln" in node.children[0]["classes"]:
                number_lines = (
                    "\n   :number-lines: "
                    + str(node.children[0].children[0]).strip()
                    + "\n"
                )

        if is_code:
            self.write(f".. code::{lang}{number_lines}\n")
        else:
            self.write("::\n\n")
        self.indent += 3
        self.allow_inlines.append(False)

    def depart_literal_block(self, node: Node) -> None:
        self.write("\n\n")
        self.indent -= 3
        allowed = self.allow_inlines.pop()
        assert not allowed

    def visit_option_list(self, node: Node) -> None:
        pass

    def depart_option_list(self, node: Node) -> None:
        self.write("\n")

    def visit_option_group(self, node: Node) -> None:
        pass

    def depart_option_group(self, node: Node) -> None:
        pass

    def visit_option_list_item(self, node: Node) -> None:
        pass

    def depart_option_list_item(self, node: Node) -> None:
        pass

    def visit_option(self, node: Node) -> None:
        if node.parent.index(node) != 0:
            self.write(", ")

    def depart_option(self, node: Node) -> None:
        pass

    def visit_option_argument(self, node: Node) -> None:
        delim = node.get("delimiter", " ")
        self.write(delim)

    def depart_option_argument(self, node: Node) -> None:
        pass

    def visit_option_string(self, node: Node) -> None:
        pass

    def depart_option_string(self, node: Node) -> None:
        pass

    def visit_description(self, node: Node) -> None:
        self.write("\n")
        self.indent += 3

    def depart_description(self, node: Node) -> None:
        self.indent -= 3

    def visit_system_message(self, node: Node) -> None:
        # TODO: improve formatting, and log at correct level.
        self.log_warning(node)

    def depart_system_message(self, node: Node) -> None:
        pass

    def visit_section(self, node: Node) -> None:
        if self.section_depth is None:
            self.section_depth = 0
        else:
            self.section_depth += 1

    def depart_section(self, node: Node) -> None:
        assert self.section_depth is not None
        if self.section_depth == 0:
            self.section_depth = None
        else:
            self.section_depth -= 1

    def visit_title(self, node: Node) -> None:
        pass

    def depart_title(self, node: Node) -> None:
        if isinstance(node.parent, (nodes.table, nodes.topic)):
            return

        assert self.section_depth is not None
        # TODO: Account for ellipsis/strong/... in title length
        length = sum(len(str(x)) for x in node.children)
        underline = self.title_underline[self.section_depth] * length
        self.write("\n" + underline + "\n")

    def visit_image(self, node: Node) -> None:
        if "uri" in node:
            arg = escape_uri(node["uri"])
        else:
            raise NotImplementedError("image without uri")

        self.write_markup_start(node, "image")
        self.write(f" {arg}\n")
        self.indent += 3
        self.write_attributes(
            node,
            ("names", "classes", "target", "alt", "height", "width", "scale"),
        )
        self.indent -= 3

    def depart_image(self, node: Node) -> None:
        pass

    def visit_reference(self, node: Node) -> None:
        reference = _Reference(self.document, node)
        if reference.text_only:
            if reference.anonymous or reference.refname is not None:
                self.write("`")
        elif not reference.image_only:
            if reference.refname is None:
                substitution = f"sub-ref-{self.reference_substitution_count}"
            else:
                substitution = reference.refname

            self.reference_substitution_count += 1
            self.reference_substitutions.append(substitution)

            suffix = "__" if reference.anonymous else "_"
            self.write(f"\\ |{substitution}|{suffix}\\ ")
            self.capture()

    def depart_reference(self, node: Node) -> None:
        reference = _Reference(self.document, node)
        if reference.text_only:
            if reference.anonymous:
                self.write("`__")
            elif reference.refname is not None:
                self.write("`_")
        elif not reference.image_only:
            captured = self.release()
            substitution = self.reference_substitutions.pop()
            self.extra_substitutions[substitution] = (
                captured.lines[0],
                reference.target,
            )

    def visit_target(self, node: Node) -> None:
        if node.children:
            self.write("_`")
        else:
            names = node["names"]
            directive = "__"

            if len(names) > 2:
                self.log_warning("target with multiple names not supported")

            if len(names) >= 1:
                name = names[0]
                directive = f".. _{name}:"

            if "refuri" in node:
                refuri = escape_uri(node["refuri"].replace("\x00", "\\"))
                self.write(f"{directive} {refuri}")
            else:
                self.write(directive)

    def depart_target(self, node: Node) -> None:
        if node.children:
            self.write("`")
        else:
            self.write("\n\n")

    def visit_note(self, node: Node) -> None:
        self.write(f".. {node.tagname}:: ")
        self.indent += 3

    visit_danger = visit_note
    visit_attention = visit_note
    visit_caution = visit_note
    visit_danger = visit_note
    visit_error = visit_note
    visit_hint = visit_note
    visit_important = visit_note
    visit_tip = visit_note
    visit_warning = visit_note

    def depart_note(self, node: Node) -> None:
        self.indent -= 3

    depart_danger = depart_note
    depart_attention = depart_note
    depart_caution = depart_note
    depart_danger = depart_note
    depart_error = depart_note
    depart_hint = depart_note
    depart_important = depart_note
    depart_tip = depart_note
    depart_warning = depart_note

    def visit_substitution_reference(self, node: Node) -> None:
        # Insert whitespace between adjacent references
        if self.needs_space(node):
            self.write(" ")

        self.write("|")

    def depart_substitution_reference(self, node: Node) -> None:
        self.write("|")

    def visit_substitution_definition(self, node: Node) -> None:
        names = node["names"]

        if not names:
            raise NotImplementedError("substitution without name")
        elif len(names) > 1:
            self.log_warning(
                "substitution with multiple names not implemented"
            )

        self.write(f".. |{names[0]}| ")
        self.indent += 3

        if len(node.children) == 1:
            child = node.children[0]

            if isinstance(child, nodes.image):
                return

        is_unicode = "ltrim" in node or "rtrim" in node

        if not is_unicode:
            is_unicode = len(node.children) > 1

            for child in node.children:
                is_unicode &= isinstance(child, nodes.Text)
                if not is_unicode:
                    break

        if is_unicode:
            self.write("unicode:: ")
        else:
            self.write("replace:: ")

    def depart_substitution_definition(self, node: Node) -> None:
        self.write("\n")
        self.write_attributes(
            node,
            (_AttrKind("ltrim", flag=True), _AttrKind("rtrim", flag=True)),
        )
        self.indent -= 3

    def visit_footnote_reference(self, node: Node) -> None:
        self.write("[")
        refname = node.get("refname", "")

        auto = node.get("auto", None)
        if auto == 1:
            self.write(f"#{refname}")
        elif auto == "*":
            assert refname == ""
            self.write("*")
        elif auto is not None:
            RstTranslator.log_warning(
                f"unsupported automatic footnote `{auto}`"
            )

    def depart_footnote_reference(self, node: Node) -> None:
        self.write("]_")

    def visit_footnote(self, node: Node) -> None:
        self.write(".. ")

        names = node.get("names", [])
        if not names:
            name = ""
        else:
            if len(names) > 1:
                RstTranslator.log_warning("multiple names not supported")
            name = names[0]

        auto = node.get("auto", None)
        if auto == 1:
            self.write(f"[#{name}] ")
        elif auto == "*":
            assert name == ""
            self.write("[*] ")
        elif auto is not None:
            RstTranslator.log_warning(
                f"unsupported automatic footnote `{auto}`"
            )

        self.indent += 3

    def depart_footnote(self, node: Node) -> None:
        self.indent -= 3

    def visit_label(self, node: Node) -> None:
        self.write("[")

    def depart_label(self, node: Node) -> None:
        self.write("] ")

    def visit_citation_reference(self, node: Node) -> None:
        self.write("[")

    def depart_citation_reference(self, node: Node) -> None:
        self.write("]_")

    def visit_citation(self, node: Node) -> None:
        self.write(".. ")
        self.indent += 3

    def depart_citation(self, node: Node) -> None:
        self.indent -= 3

    def visit_comment(self, node: Node) -> None:
        self.write(".. ")
        self.indent += 3

    def depart_comment(self, node: Node) -> None:
        self.indent -= 3
        self.write("\n\n")

    def visit_line_block(self, node: Node) -> None:
        self.line_block_indent += 1

    def depart_line_block(self, node: Node) -> None:
        assert self.line_block_indent >= 1
        self.line_block_indent -= 1
        if not isinstance(node.parent, nodes.line_block):
            self.write("\n")

    def visit_line(self, node: Node) -> None:
        prefix = "|" + (" " * self.line_block_indent)
        self.write(prefix)
        self.indent += len(prefix)

    def depart_line(self, node: Node) -> None:
        self.indent -= self.line_block_indent + 1
        self.write("\n")

    def visit_doctest_block(self, node: Node) -> None:
        pass

    def depart_doctest_block(self, node: Node) -> None:
        self.write("\n\n")

    def visit_table(self, node: Node) -> None:
        self.write(".. table::")
        self.indent += 3

        children = node.children

        if isinstance(children[0], nodes.title):
            self.write(" ")
            children[0].walkabout(self)
            children = children[1:]

        self.write("\n")

        # TODO: Implement stub columns

        self.write_attributes(
            node,
            ("classes",),
        )

        if "colwidths-given" in node.get("classes", []):
            # TODO: Implement this.
            self.log_warning("table with explicit widths not yet supported")

        for child in children:
            if isinstance(child, nodes.title):
                raise NotImplementedError("multiple table titles")

            child.walkabout(self)

        raise nodes.SkipChildren

    def depart_table(self, node: Node) -> None:
        self.write("\n\n")
        self.indent -= 3

    def visit_tgroup(self, node: Node) -> None:
        column_widths: List[int] = []

        for child in node.children:
            if not isinstance(child, nodes.colspec):
                continue
            column_widths.append(child["colwidth"])

        assert self.table is None
        assert len(column_widths) == node["cols"]

        self.table = Table(column_widths=column_widths)

    def depart_tgroup(self, node: Node) -> None:
        assert self.table is not None
        # TODO: Write the table I guess?
        rendered = "\n".join(self.table.render())
        self.table = None
        self.write(rendered)

    def visit_colspec(self, node: Node) -> None:
        pass

    def depart_colspec(self, node: Node) -> None:
        pass

    def visit_thead(self, node: Node) -> None:
        assert self.table is not None
        assert not self.table.in_header
        self.table.in_header = True
        self.write("\n\n")

    def depart_thead(self, node: Node) -> None:
        assert self.table is not None
        assert self.table.in_header
        self.table.in_header = False

    def visit_tbody(self, node: Node) -> None:
        if self.lines[-1]:
            # XXX: Need to write newlines after `.. table::` if there isn't a
            #      `thead` element.
            self.write("\n\n")

    def depart_tbody(self, node: Node) -> None:
        pass  # TODO

    def visit_row(self, node: Node) -> None:
        assert self.table is not None
        self.table.rows.append([])

    def depart_row(self, node: Node) -> None:
        pass

    def visit_entry(self, node: Node) -> None:
        self.capture()

    def depart_entry(self, node: Node) -> None:
        captured = self.release()

        assert self.table is not None
        cell = CellContent(
            lines=captured.lines,
            header=self.table.in_header,
            morecols=node.get("morecols", 0),
            morerows=node.get("morerows", 0),
        )

        self.table.rows[-1].append(cell)

    def visit_title_reference(self, node: Node) -> None:
        self.write(":title-reference:`")

    def depart_title_reference(self, node: Node) -> None:
        self.write("`")

    def visit_transition(self, node: Node) -> None:
        self.write("\n\n----\n\n")

    def depart_transition(self, node: Node) -> None:
        pass

    def visit_inline(self, node: Node) -> None:
        if isinstance(node.parent, nodes.literal_block):
            if "ln" in node["classes"]:
                raise nodes.SkipNode

        self.allow_inlines.append(False)

        if not self.allow_inlines[-2]:
            return

        classes = tuple(sorted(set(node["classes"])))

        try:
            name = self.extra_roles[classes]
        except KeyError:
            name = f"inline-{self.role_count}"
            self.role_count += 1
            self.extra_roles[classes] = name

        self.write(f":{name}:`")

    def depart_inline(self, node: Node) -> None:
        allowed = self.allow_inlines.pop()
        assert not allowed

        if self.allow_inlines[-1]:
            self.write("` ")

    def visit_problematic(self, node: Node) -> None:
        # TODO
        pass

    def depart_problematic(self, node: Node) -> None:
        # TODO
        pass

    def visit_superscript(self, node: Node) -> None:
        self.write("\\ :superscript:`")

    def depart_superscript(self, node: Node) -> None:
        self.write("`\\ ")

    def visit_subscript(self, node: Node) -> None:
        self.write("\\ :subscript:`")

    def depart_subscript(self, node: Node) -> None:
        self.write("`\\ ")

    def visit_math(self, node: Node) -> None:
        self.write("\\ :math:`")

    def depart_math(self, node: Node) -> None:
        self.write("`\\ ")

    def visit_math_block(self, node: Node) -> None:
        self.write(".. math::\n\n")
        self.indent += 3

    def depart_math_block(self, node: Node) -> None:
        self.write("\n\n")
        self.indent -= 3

    def visit_topic(self, node: Node) -> None:
        self.write(".. topic::")
        self.indent += 3

        children = node.children

        if isinstance(children[0], nodes.title):
            self.write(" ")
            children[0].walkabout(self)
            children = children[1:]

        self.write("\n\n")

        for child in children:
            if isinstance(child, nodes.title):
                raise NotImplementedError("multiple topic titles")

            child.walkabout(self)

        raise nodes.SkipChildren

    def depart_topic(self, node: Node) -> None:
        self.write("\n\n")
        self.indent -= 3
