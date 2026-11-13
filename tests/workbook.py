"""A one-sheet workbook built in memory, and the calculations the smoke tests run on it."""

import io
import zipfile

import rulex_engine as rx

# Sheet "Calc" holds 2 in A1, =A1*21 in B1 and =SUM(A1:B1)&"x" in C1.
SHEET = (
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<sheetData><row r="1"><c r="A1"><v>2</v></c><c r="B1"><f>A1*21</f></c>'
    '<c r="C1"><f>SUM(A1:B1)&amp;"x"</f></c></row></sheetData></worksheet>'
)
PARTS = {
    "[Content_Types].xml": (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    ),
    "_rels/.rels": (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    ),
    "xl/workbook.xml": (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Calc" sheetId="1" r:id="rId1"/></sheets></workbook>'
    ),
    "xl/_rels/workbook.xml.rels": (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    ),
    "xl/worksheets/sheet1.xml": SHEET,
}
A1 = rx.CellRef("Calc", "A1")
B1 = rx.CellRef("Calc", "B1")
C1 = rx.CellRef("Calc", "C1")


def workbook():
    """Return the workbook as .xlsx bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in PARTS.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def expected(x):
    """Return the values B1 and C1 hold when A1 is x."""
    return x * 21, f"{x * 22:g}x"


def calculate(calc, x):
    """Run calc with A1 set to x and return B1 and C1."""
    out = calc.run({A1: x}, [B1, C1]).output
    return out[B1], out[C1]


def calculate_in_child(x):
    """Build a calculator in the current process and return B1 and C1 for A1 = x.

    A child process started with spawn imports this module by name, so the
    function must live at module level.
    """
    return calculate(rx.build_calculator(workbook()), x)
