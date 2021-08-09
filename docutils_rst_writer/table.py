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
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(eq=False)
class CellContent:
    lines: List[str]
    header: bool
    morecols: int
    morerows: int

    @property
    def content_width(self) -> int:
        if self.lines:
            return max(len(line) for line in self.lines)
        else:
            return 0

    @property
    def content_height(self) -> int:
        return len(self.lines)


@dataclass(eq=False)
class TreeCell:
    content: CellContent
    row: int
    column: int
    children: List[TreeCell] = field(default_factory=list)


@dataclass(eq=False)
class TreeTable:
    header_row: Optional[int] = None
    row_heights: List[int] = field(default_factory=list)
    column_widths: List[int] = field(default_factory=list)
    top_row: List[TreeCell] = field(default_factory=list)


@dataclass
class Table:
    column_widths: List[int]
    in_header: bool = False
    rows: List[List[CellContent]] = field(default_factory=list)

    @staticmethod
    def row_divider(column: int, width: int, header: bool) -> str:
        divider = ""
        if column == 0:
            divider += "+"

        if header:
            divider += "=" * width
        else:
            divider += "-" * width

        divider += "+"
        return divider

    def treeify(self) -> TreeTable:
        if not self.rows:
            return TreeTable()

        header_row: Optional[int] = None
        row_heights: Dict[int, int] = defaultdict(lambda: 0)
        column_widths: Dict[int, int] = defaultdict(lambda: 0)

        for idx, width in enumerate(self.column_widths):
            column_widths[idx] = width

        # Index of the next unused cell in a row.
        in_column_indexes = [0 for _ in self.rows]

        # Number of columns to the left of the next unused cell in a row.
        in_columns = [0 for _ in self.rows]

        # Cells that exist in the top row of the table.
        top_row: List[TreeCell] = []

        # Cells which span multiple rows or columns.
        rowspans: List[TreeCell] = []
        colspans: List[TreeCell] = []

        for cell in self.rows[0]:
            first = TreeCell(content=cell, row=0, column=in_columns[0])
            top_row.append(first)

            stack = [first]

            while stack:
                current = stack[-1]

                end_column = current.column + current.content.morecols + 1
                end_row = current.row + current.content.morerows + 1

                if (
                    end_row < len(in_columns)
                    and in_columns[end_row] < end_column
                ):
                    # Still children to visit.
                    in_col_off = in_column_indexes[end_row]
                    child = TreeCell(
                        content=self.rows[end_row][in_col_off],
                        row=end_row,
                        column=in_columns[end_row],
                    )
                    stack.append(child)
                    current.children.append(child)
                else:
                    # No more children.
                    stack.pop()

                    in_column_indexes[current.row] += 1

                    for row_idx in range(current.row, end_row):
                        assert in_columns[row_idx] <= end_column
                        in_columns[row_idx] = end_column

                    if current.content.header:
                        if header_row is None or current.row > header_row:
                            header_row = current.row

                    if current.content.morecols == 0:
                        column_widths[current.column] = max(
                            column_widths[current.column],
                            current.content.content_width,
                        )
                    else:
                        colspans.append(current)

                    if current.content.morerows == 0:
                        row_heights[current.row] = max(
                            row_heights[current.row],
                            current.content.content_height,
                        )
                    else:
                        rowspans.append(current)

        # Convert from dicts to lists.
        row_heights_list = []
        for idx in range(1 + max(row_heights.keys())):
            row_heights_list.append(row_heights[idx])

        column_widths_list = []
        for idx in range(1 + max(column_widths.keys())):
            column_widths_list.append(column_widths[idx])

        # Expand rows/columns containing a spanning cell.
        for current in rowspans:
            cumulative_height = row_heights_list[current.row]
            end_row = current.row + current.content.morerows + 1
            for height in row_heights_list[current.row + 1 : end_row]:
                cumulative_height += height
                cumulative_height += 1  # Account for divider.

            if cumulative_height < current.content.content_height:
                extra = current.content.content_height - cumulative_height
                row_heights_list[current.row] += extra

        for current in colspans:
            cumulative_width = column_widths_list[current.column]
            end_column = current.column + current.content.morecols + 1
            for width in column_widths_list[current.column + 1 : end_column]:
                cumulative_width += width
                cumulative_width += 1  # Account for divider.

            if cumulative_width < current.content.content_width:
                extra = current.content.content_width - cumulative_width
                column_widths_list[current.column] += extra

        return TreeTable(
            top_row=top_row,
            column_widths=column_widths_list,
            row_heights=row_heights_list,
            header_row=header_row,
        )

    def render(self) -> List[str]:
        tree = self.treeify()

        line_count = sum(tree.row_heights) + len(tree.row_heights) + 1
        lines: List[List[str]] = [[] for _ in range(line_count)]

        stack: List[TreeCell] = list(tree.top_row)
        stack.reverse()

        while stack:
            current = stack.pop()
            stack.extend(reversed(current.children))

            cell = current.content

            width = cell.morecols  # Account for dividers
            width += sum(
                tree.column_widths[
                    current.column : current.column + cell.morecols + 1
                ]
            )

            height = cell.morerows  # Account for dividers
            height += sum(
                tree.row_heights[current.row : current.row + cell.morerows + 1]
            )

            line_offset = 1 + current.row
            line_offset += sum(tree.row_heights[: current.row])

            left = len(lines[line_offset])

            prefix = ""
            if current.column == 0:
                prefix = "|"

            for idx in range(height):
                try:
                    line = cell.lines[idx]
                except IndexError:
                    line = ""

                line = line.ljust(width) + "|"
                lines[line_offset + idx].extend(prefix + line)

            # Draw top divider.
            if current.row == 0:
                lines[0].extend(self.row_divider(current.column, width, False))

            # Draw dividers between rows.
            header_row = current.row == tree.header_row
            lines[line_offset + idx + 1].extend(
                self.row_divider(
                    current.column,
                    width,
                    header_row,
                )
            )

            lines[line_offset - 1][left - 1] = "+"

        return ["".join(line) for line in lines]
