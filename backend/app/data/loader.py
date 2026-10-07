from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from app.data.contracts import FileStatus, FileValidation, ValidationIssue

EXPECTED_FILE_NAMES = (
    "fields.csv",
    "service_orders.csv",
    "ndvi_metadata.csv",
    "LAYER_MAP_PLANTING.csv",
    "LAYER_MAP_FERTILIZATION.csv",
    "service_orders_fields.csv",
    "soil_analysis.csv",
)


@dataclass(frozen=True)
class CsvInput:
    name: str
    content: bytes


@dataclass
class LoadedCsv:
    frame: pd.DataFrame
    file: FileValidation
    warnings: list[ValidationIssue]


class PackageValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        super().__init__("Pacote de arquivos inválido.")
        self.issues = issues


class PackageTooLargeError(PackageValidationError):
    pass


class CsvLoadError(ValueError):
    def __init__(self, issue: ValidationIssue) -> None:
        super().__init__(issue.message)
        self.issue = issue


def validate_package_files(files: list[CsvInput], max_upload_mb: int) -> dict[str, bytes]:
    total_bytes = sum(len(item.content) for item in files)
    max_bytes = max_upload_mb * 1024 * 1024
    if total_bytes > max_bytes:
        raise PackageTooLargeError(
            [
                ValidationIssue(
                    code="package_too_large",
                    message=f"O pacote excede o limite de {max_upload_mb} MB.",
                )
            ]
        )

    issues: list[ValidationIssue] = []
    grouped: dict[str, list[CsvInput]] = {}
    for item in files:
        grouped.setdefault(item.name, []).append(item)
        if item.name not in EXPECTED_FILE_NAMES:
            issues.append(
                ValidationIssue(
                    code="unexpected_file",
                    message=f"Arquivo não esperado: {item.name}.",
                    file=item.name,
                )
            )

    for name in EXPECTED_FILE_NAMES:
        matches = grouped.get(name, [])
        if not matches:
            issues.append(
                ValidationIssue(
                    code="missing_file",
                    message=f"Arquivo obrigatório ausente: {name}.",
                    file=name,
                )
            )
        elif len(matches) > 1:
            issues.append(
                ValidationIssue(
                    code="duplicate_file",
                    message=f"Arquivo enviado mais de uma vez: {name}.",
                    file=name,
                )
            )

    if issues:
        raise PackageValidationError(issues)

    return {name: grouped[name][0].content for name in EXPECTED_FILE_NAMES}


def load_csv(name: str, content: bytes) -> LoadedCsv:
    if name not in EXPECTED_FILE_NAMES:
        raise CsvLoadError(
            ValidationIssue(code="unexpected_file", message=f"Arquivo não esperado: {name}.", file=name)
        )
    if not content:
        raise CsvLoadError(
            ValidationIssue(code="unreadable_csv", message="O CSV está vazio.", file=name)
        )
    if b"\x00" in content:
        raise CsvLoadError(
            ValidationIssue(code="unreadable_csv", message="O arquivo não contém texto CSV válido.", file=name)
        )

    warnings: list[ValidationIssue] = []
    try:
        text = content.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = content.decode("latin-1")
        encoding = "latin-1"
        warnings.append(
            ValidationIssue(
                code="alternative_encoding",
                message="O arquivo foi lido com encoding Latin-1.",
                file=name,
            )
        )

    delimiter = _detect_delimiter(text, name)
    try:
        frame = pd.read_csv(
            StringIO(text),
            sep=delimiter,
            dtype=str,
            keep_default_na=True,
            na_values=[""],
        )
    except (EmptyDataError, ParserError, UnicodeError, ValueError) as exc:
        raise CsvLoadError(
            ValidationIssue(code="unreadable_csv", message="Não foi possível interpretar o CSV.", file=name)
        ) from exc

    frame.columns = [str(column).strip() for column in frame.columns]
    if not len(frame.columns) or any(not column for column in frame.columns):
        raise CsvLoadError(
            ValidationIssue(code="unreadable_csv", message="O CSV não possui cabeçalho válido.", file=name)
        )

    return LoadedCsv(
        frame=frame,
        file=FileValidation(
            name=name,
            status=FileStatus.VALID,
            size_bytes=len(content),
            rows=len(frame),
            encoding=encoding,
            delimiter=delimiter,
        ),
        warnings=warnings,
    )


def _detect_delimiter(text: str, name: str) -> str:
    sample = text[:8192]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error as exc:
        raise CsvLoadError(
            ValidationIssue(
                code="unreadable_csv",
                message="Não foi possível detectar vírgula ou ponto e vírgula como delimitador.",
                file=name,
            )
        ) from exc
    return delimiter
