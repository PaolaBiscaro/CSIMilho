import pandas as pd
import pytest

from app.data.loader import (
    CsvInput,
    CsvLoadError,
    PackageTooLargeError,
    PackageValidationError,
    load_csv,
    validate_package_files,
)


@pytest.mark.parametrize(
    ("delimiter", "content"),
    [
        (",", b"idField,fieldName\n1,Area A\n"),
        (";", b"idField;fieldName\n1;Area A\n"),
    ],
)
def test_load_csv_detects_supported_delimiters(delimiter: str, content: bytes) -> None:
    loaded = load_csv("fields.csv", content)

    assert loaded.file.delimiter == delimiter
    assert loaded.frame.to_dict(orient="records") == [{"idField": "1", "fieldName": "Area A"}]


def test_load_csv_uses_latin_1_with_warning() -> None:
    loaded = load_csv("fields.csv", "idField;fieldName\n1;Grão\n".encode("latin-1"))

    assert loaded.file.encoding == "latin-1"
    assert loaded.warnings[0].code == "alternative_encoding"
    assert loaded.frame.loc[0, "fieldName"] == "Grão"


def test_load_csv_does_not_replace_invalid_values_with_zero() -> None:
    loaded = load_csv("fields.csv", b"idField,fieldName\nnot-a-number,Area A\n")

    assert loaded.frame.loc[0, "idField"] == "not-a-number"
    assert not pd.isna(loaded.frame.loc[0, "idField"])


def test_load_soil_csv_accepts_bom_semicolon_and_preserves_decimal_comma() -> None:
    content = "\ufeffAMOSTRA;PHCACL2\n1;5,23\n".encode("utf-8")

    loaded = load_csv("soil_analysis.csv", content)

    assert loaded.file.encoding == "utf-8-sig"
    assert loaded.file.delimiter == ";"
    assert loaded.frame.loc[0, "PHCACL2"] == "5,23"


@pytest.mark.parametrize("content", [b"", b"\x00\x00\x00", b"only-one-column\nvalue\n"])
def test_load_csv_rejects_unreadable_content(content: bytes) -> None:
    with pytest.raises(CsvLoadError) as error:
        load_csv("fields.csv", content)

    assert error.value.issue.code == "unreadable_csv"


def complete_package() -> list[CsvInput]:
    return [
        CsvInput("fields.csv", b"a,b\n1,2"),
        CsvInput("service_orders.csv", b"a,b\n1,2"),
        CsvInput("ndvi_metadata.csv", b"a,b\n1,2"),
        CsvInput("LAYER_MAP_PLANTING.csv", b"a,b\n1,2"),
        CsvInput("LAYER_MAP_FERTILIZATION.csv", b"a,b\n1,2"),
        CsvInput("service_orders_fields.csv", b"a,b\n1,2"),
        CsvInput("soil_analysis.csv", b"a;b\n1;2"),
    ]


def test_validate_package_requires_each_allowed_name_once() -> None:
    package = complete_package()
    package.pop()
    package.append(CsvInput("other.csv", b"a,b\n1,2"))

    with pytest.raises(PackageValidationError) as error:
        validate_package_files(package, max_upload_mb=1)

    assert {issue.code for issue in error.value.issues} == {"missing_file", "unexpected_file"}


def test_validate_package_enforces_total_size() -> None:
    package = complete_package()

    with pytest.raises(PackageTooLargeError):
        validate_package_files(package, max_upload_mb=0)


def test_validate_package_requires_soil_analysis() -> None:
    package = [item for item in complete_package() if item.name != "soil_analysis.csv"]

    with pytest.raises(PackageValidationError) as error:
        validate_package_files(package, max_upload_mb=1)

    assert [(issue.code, issue.file) for issue in error.value.issues] == [
        ("missing_file", "soil_analysis.csv")
    ]
