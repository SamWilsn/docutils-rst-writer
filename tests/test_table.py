from docutils_rst_writer.table import CellContent, Table


def test_treeify_rowspan() -> None:
    table = Table(column_widths=[5, 7])

    table.rows = [
        [
            CellContent(
                lines=["a", "b", "c"], header=False, morecols=0, morerows=1
            ),
            CellContent(
                lines=["hello world"], header=False, morecols=0, morerows=0
            ),
        ],
        [
            CellContent(lines=["d"], header=False, morecols=0, morerows=0),
        ],
    ]

    tree_table = table.treeify()

    assert tree_table.column_widths == [5, 11]
    assert tree_table.row_heights == [1, 1]

    assert 2 == len(tree_table.top_row)

    top_first = tree_table.top_row[0]

    assert top_first.content.lines == ["a", "b", "c"]
    assert top_first.content.morecols == 0
    assert top_first.content.morerows == 1
    assert not top_first.content.header

    assert top_first.row == 0
    assert top_first.column == 0

    assert top_first.children == []

    top_second = tree_table.top_row[1]

    assert top_second.content.lines == ["hello world"]
    assert top_second.content.morecols == 0
    assert top_second.content.morerows == 0
    assert not top_second.content.header

    assert top_second.row == 0
    assert top_second.column == 1

    assert 1 == len(top_second.children)

    bottom = top_second.children[0]

    assert bottom.content.lines == ["d"]
    assert bottom.content.morecols == 0
    assert bottom.content.morerows == 0
    assert not bottom.content.header

    assert bottom.row == 1
    assert bottom.column == 1

    assert bottom.children == []


def test_treeify_colspan() -> None:
    table = Table(column_widths=[5, 7])

    table.rows = [
        [
            CellContent(
                lines=["a", "b", "c"], header=False, morecols=1, morerows=0
            ),
        ],
        [
            CellContent(
                lines=["hello world"], header=False, morecols=0, morerows=0
            ),
            CellContent(lines=["d"], header=False, morecols=0, morerows=0),
        ],
    ]

    tree_table = table.treeify()

    assert tree_table.row_heights == [3, 1]
    assert tree_table.column_widths == [11, 7]

    assert 1 == len(tree_table.top_row)

    top_cell = tree_table.top_row[0]

    assert top_cell.content.lines == ["a", "b", "c"]
    assert top_cell.content.morecols == 1
    assert top_cell.content.morerows == 0
    assert not top_cell.content.header

    assert top_cell.row == 0
    assert top_cell.column == 0

    assert 2 == len(top_cell.children)

    first = top_cell.children[0]

    assert first.content.lines == ["hello world"]
    assert first.content.morecols == 0
    assert first.content.morerows == 0
    assert not first.content.header

    assert first.row == 1
    assert first.column == 0

    assert first.children == []

    second = top_cell.children[1]

    assert second.content.lines == ["d"]
    assert second.content.morecols == 0
    assert second.content.morerows == 0
    assert not second.content.header

    assert second.row == 1
    assert second.column == 1

    assert second.children == []


def test_treeify_rowspan_expand() -> None:
    table = Table(column_widths=[5, 7])

    table.rows = [
        [
            CellContent(lines=["a"] * 4, header=False, morecols=0, morerows=1),
            CellContent(lines=["d"], header=False, morecols=0, morerows=0),
        ],
        [
            CellContent(lines=["d"], header=False, morecols=0, morerows=0),
        ],
    ]

    tree = table.treeify()

    assert tree.column_widths == [5, 7]
    assert tree.row_heights == [2, 1]


def test_treeify_colspan_expand() -> None:
    table = Table(column_widths=[4, 3])

    table.rows = [
        [
            CellContent(
                lines=["aaaaaaaaa"], header=False, morerows=0, morecols=1
            ),
        ],
        [
            CellContent(lines=["d"], header=False, morerows=0, morecols=0),
            CellContent(lines=["e"], header=False, morerows=0, morecols=0),
        ],
    ]

    tree = table.treeify()

    assert tree.column_widths == [5, 3]
    assert tree.row_heights == [1, 1]
