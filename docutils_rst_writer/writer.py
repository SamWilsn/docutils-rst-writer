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

from __future__ import (
    absolute_import,
    annotations,
    print_function,
    unicode_literals,
)

import logging
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from docutils import nodes, writers
from docutils.nodes import Node
from docutils.nodes import document as Document
from docutils.utils import roman


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


class RstTranslator(nodes.NodeVisitor):
    lines: List[str]
    indent: int
    section_depth: Optional[int]
    title_underline: str = "=-~#_`:.'^*+\""

    def __init__(self, document: Document) -> None:
        super().__init__(document)
        self.lines = [""]
        self.indent = 0
        self.section_depth = None

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

    def write_attributes(
        self,
        node: Node,
        attrs: Tuple[Union[str, Tuple[str, str]], ...],
    ) -> None:
        if "names" in node:
            if len(node["names"]) > 1:
                RstTranslator.log_warning("multiple names not supported")

            if len(node["names"]) > 0:
                name = node["names"][0]
                self.write(f":name: {name}\n")

        if "classes" in node:
            classes = " ".join(node["classes"])

            if classes:
                self.write(f":class: {classes}\n")

        for item in attrs:
            if isinstance(item, tuple):
                (node_attr, rst_attr) = item
            else:
                node_attr = item
                rst_attr = item

            if node_attr not in node:
                continue

            value = node[node_attr]

            if value is None:
                self.write(f":{rst_attr}:\n")
            else:
                self.write(f":{rst_attr}: {value}\n")

    def visit_document(self, node: Node) -> None:
        pass

    def depart_document(self, node: Node) -> None:
        pass

    def visit_paragraph(self, node: Node) -> None:
        pass

    def depart_paragraph(self, node: Node) -> None:
        self.write("\n\n")

    def visit_Text(self, node: Node) -> None:
        self.write(str(node).replace("\x00", "\\"))

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
        pass

    def visit_enumerated_list(self, node: Node) -> None:
        pass

    def depart_enumerated_list(self, node: Node) -> None:
        pass

    def visit_list_item(self, node: Node) -> None:
        item = _ListItem(node)
        formatted = item.format() + " "
        self.write(formatted)
        self.indent += len(formatted)

    def depart_list_item(self, node: Node) -> None:
        item = _ListItem(node)
        formatted = item.format() + " "
        self.indent -= len(formatted)

    def visit_literal_block(self, node: Node) -> None:
        self.write("::\n\n")
        self.indent += 3

    def depart_literal_block(self, node: Node) -> None:
        self.write("\n\n")
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
        assert self.section_depth is not None
        length = len(str(node))
        underline = self.title_underline[self.section_depth] * length
        self.write("\n" + underline * length + "\n")

    def visit_image(self, node: Node) -> None:
        if "uri" in node:
            arg = escape_uri(node["uri"])
        elif "target" in node.attributes:
            arg = node["target"]
        else:
            raise NotImplementedError("image without uri/target")

        self.write(f".. image:: {arg}\n")
        self.indent += 3
        self.write_attributes(node, ("alt", "height", "width", "scale"))
        self.indent -= 3

    def depart_image(self, node: Node) -> None:
        pass

    def visit_note(self, node: Node) -> None:
        print(node)
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
