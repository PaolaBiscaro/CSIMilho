from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.data.contracts import (
    DatasetStatus,
    DatasetValidationResponse,
    FieldManagement,
    FieldPurpose,
    FileStatus,
    FileValidation,
    OperationLinkage,
    ValidPair,
    ValidationIssue,
)
from app.data.linker import build_service_order_catalog, build_service_order_mapping, link_ndvi_seasons
from app.data.loader import (
    EXPECTED_FILE_NAMES,
    CsvInput,
    CsvLoadError,
    PackageTooLargeError,
    PackageValidationError,
    load_csv,
    validate_package_files,
)
from app.data.normalizer import normalize_fertilization, normalize_fields, normalize_ndvi, normalize_planting
from app.data.session_store import NormalizedDataset, dataset_store

router = APIRouter(prefix="/api", tags=["datasets"])


@router.post("/datasets", response_model=DatasetValidationResponse, status_code=201)
async def create_dataset(files: list[UploadFile] = File(...)):
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    inputs = [
        CsvInput(name=upload.filename or "", content=await upload.read(max_bytes + 1))
        for upload in files
    ]
    try:
        package = validate_package_files(inputs, settings.max_upload_mb)
    except PackageTooLargeError as exc:
        response = _invalid_package_response(inputs, exc.issues)
        return JSONResponse(status_code=413, content=response.model_dump(mode="json"))
    except PackageValidationError as exc:
        response = _invalid_package_response(inputs, exc.issues)
        return JSONResponse(status_code=422, content=response.model_dump(mode="json"))

    response = _process_package(package)
    status_code = 201 if response.status is not DatasetStatus.ERROR else 422
    if status_code == 422:
        return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))
    return response


def _process_package(package: dict[str, bytes]) -> DatasetValidationResponse:
    loaded = {}
    file_results: list[FileValidation] = []
    warnings: list[ValidationIssue] = []
    errors: list[ValidationIssue] = []
    for name in EXPECTED_FILE_NAMES:
        try:
            item = load_csv(name, package[name])
        except CsvLoadError as exc:
            file_results.append(
                FileValidation(name=name, status=FileStatus.INVALID, size_bytes=len(package[name]))
            )
            errors.append(exc.issue)
            continue
        loaded[name] = item.frame
        file_results.append(item.file)
        warnings.extend(item.warnings)

    if errors:
        return _validation_response(file_results=file_results, warnings=warnings, errors=errors)

    field_result = normalize_fields(loaded["fields.csv"])
    warnings.extend(field_result.warnings)
    errors.extend(field_result.errors)

    service_order_catalog = build_service_order_catalog(loaded["service_orders.csv"])
    warnings.extend(service_order_catalog.warnings)
    errors.extend(service_order_catalog.errors)

    service_order_result = build_service_order_mapping(
        loaded["service_orders_fields.csv"],
        field_result.fields,
    )
    warnings.extend(service_order_result.warnings)
    errors.extend(service_order_result.errors)
    errors.extend(
        ValidationIssue(
            code="unknown_service_order",
            message=f"A ordem {service_order_id} não existe em service_orders.csv.",
            file="service_orders_fields.csv",
        )
        for service_order_id in sorted(
            set(service_order_result.mapping) - set(service_order_catalog.operation_by_id)
        )
    )

    planting_result = normalize_planting(
        loaded["LAYER_MAP_PLANTING.csv"],
        service_order_catalog.number_to_id,
        service_order_result.mapping,
        field_result.geometries,
    )
    fertilization_result = normalize_fertilization(
        loaded["LAYER_MAP_FERTILIZATION.csv"],
        service_order_catalog.number_to_id,
        service_order_result.mapping,
        field_result.geometries,
    )
    warnings.extend(planting_result.warnings + fertilization_result.warnings)
    errors.extend(planting_result.errors + fertilization_result.errors)

    ndvi_result = normalize_ndvi(loaded["ndvi_metadata.csv"])
    warnings.extend(ndvi_result.warnings)
    errors.extend(ndvi_result.errors)
    spatial_result = link_ndvi_seasons(ndvi_result.frame, field_result.fields)
    warnings.extend(spatial_result.warnings)
    errors.extend(spatial_result.errors)

    valid_pairs = _build_available_pairs(
        field_result.fields,
        spatial_result.frame,
        planting_result.frame,
        fertilization_result.frame,
    )
    if not valid_pairs:
        errors.append(
            ValidationIssue(
                code="no_valid_pairs",
                message="Nenhum par com mesma finalidade e manejos diferentes está disponível.",
            )
        )

    available_operations = sorted(
        set(planting_result.frame.get("operation", []))
        | set(fertilization_result.frame.get("operation", []))
    )
    warnings.extend(_operation_coverage_warnings(fertilization_result.frame))
    warnings.append(
        ValidationIssue(
            code="no_reliable_productivity",
            message="O pacote não possui produtividade confiável; nenhuma conclusão de produtividade será feita.",
        )
    )
    operation_linkage = _sum_operation_linkage(
        planting_result.linkage,
        fertilization_result.linkage,
    )

    if errors:
        _mark_invalid_files(file_results, errors)
        return _validation_response(
            file_results=file_results,
            fields=field_result.fields,
            valid_pairs=valid_pairs,
            available_operations=available_operations,
            operation_linkage=operation_linkage,
            warnings=warnings,
            errors=errors,
        )

    dataset = NormalizedDataset(
        fields=field_result.fields,
        ndvi_observations=spatial_result.frame,
        planting_operations=planting_result.frame,
        fertilization_operations=fertilization_result.frame,
        service_order_number_mapping=service_order_catalog.number_to_id,
        service_order_operations=service_order_catalog.operation_by_id,
        service_order_mapping=service_order_result.mapping,
        season_links=spatial_result.links,
        dataset_metadata={
            "source_files": list(EXPECTED_FILE_NAMES),
            "file_validation": [item.model_dump(mode="json") for item in file_results],
            "warnings": [item.model_dump(mode="json") for item in warnings],
            "operation_linkage_by_file": {
                "LAYER_MAP_PLANTING.csv": planting_result.linkage.model_dump(),
                "LAYER_MAP_FERTILIZATION.csv": fertilization_result.linkage.model_dump(),
            },
        },
    )
    dataset_id = dataset_store.save(dataset)
    return DatasetValidationResponse(
        dataset_id=dataset_id,
        status=DatasetStatus.READY_WITH_WARNINGS if warnings else DatasetStatus.READY,
        quality_score=_quality_score(warnings, []),
        files=file_results,
        fields=field_result.fields,
        valid_pairs=valid_pairs,
        available_operations=available_operations,
        operation_linkage=operation_linkage,
        warnings=warnings,
        errors=[],
    )


def _build_structural_pairs(fields) -> list[ValidPair]:
    pairs: list[ValidPair] = []
    for target in fields:
        for reference in fields:
            if target.field_id == reference.field_id:
                continue
            if target.management is not FieldManagement.DIGITAL:
                continue
            if reference.management is not FieldManagement.CONVENTIONAL:
                continue
            if target.purpose is FieldPurpose.UNKNOWN or target.purpose is not reference.purpose:
                continue
            if target.management is FieldManagement.UNKNOWN or reference.management is FieldManagement.UNKNOWN:
                continue
            if target.management is reference.management:
                continue
            pairs.append(
                ValidPair(
                    target_field_id=target.field_id,
                    reference_field_id=reference.field_id,
                    purpose=target.purpose,
                )
            )
    return pairs


def _build_available_pairs(fields, ndvi_frame, planting_frame, fertilization_frame) -> list[ValidPair]:
    ndvi_fields = set(ndvi_frame.get("field_id", []))
    planting_fields = set(planting_frame.get("field_id", []))
    fertilization_fields = set(fertilization_frame.get("field_id", []))
    available_fields = ndvi_fields & planting_fields & fertilization_fields
    return [
        pair
        for pair in _build_structural_pairs(fields)
        if pair.target_field_id in available_fields and pair.reference_field_id in available_fields
    ]


def _sum_operation_linkage(*items: OperationLinkage) -> OperationLinkage:
    return OperationLinkage(
        assigned_rows=sum(item.assigned_rows for item in items),
        unassigned_rows=sum(item.unassigned_rows for item in items),
        invalid_geometry_rows=sum(item.invalid_geometry_rows for item in items),
        ambiguous_rows=sum(item.ambiguous_rows for item in items),
    )


def _operation_coverage_warnings(frame) -> list[ValidationIssue]:
    if frame.empty:
        return []
    warnings: list[ValidationIssue] = []
    for operation, group in frame.groupby("operation"):
        if group["field_id"].nunique() == 1:
            warnings.append(
                ValidationIssue(
                    code="operation_single_field",
                    message=f"A operação {operation} está disponível em apenas um talhão.",
                    file="LAYER_MAP_FERTILIZATION.csv",
                )
            )
    return warnings


def _mark_invalid_files(files: list[FileValidation], errors: list[ValidationIssue]) -> None:
    invalid_names = {issue.file for issue in errors if issue.file}
    for item in files:
        if item.name in invalid_names:
            item.status = FileStatus.INVALID


def _validation_response(
    *,
    file_results: list[FileValidation],
    fields=None,
    valid_pairs=None,
    available_operations=None,
    operation_linkage=None,
    warnings=None,
    errors=None,
) -> DatasetValidationResponse:
    warnings = warnings or []
    errors = errors or []
    return DatasetValidationResponse(
        dataset_id=None,
        status=DatasetStatus.ERROR,
        quality_score=_quality_score(warnings, errors),
        files=file_results,
        fields=fields or [],
        valid_pairs=valid_pairs or [],
        available_operations=available_operations or [],
        operation_linkage=operation_linkage or OperationLinkage(),
        warnings=warnings,
        errors=errors,
    )


def _invalid_package_response(
    inputs: list[CsvInput],
    errors: list[ValidationIssue],
) -> DatasetValidationResponse:
    counts = Counter(item.name for item in inputs)
    sizes = {item.name: len(item.content) for item in inputs}
    files = []
    for name in EXPECTED_FILE_NAMES:
        count = counts[name]
        status = FileStatus.MISSING if count == 0 else FileStatus.RECEIVED
        if count > 1:
            status = FileStatus.INVALID
        files.append(FileValidation(name=name, status=status, size_bytes=sizes.get(name, 0)))
    return _validation_response(file_results=files, errors=errors)


def _quality_score(warnings: list[ValidationIssue], errors: list[ValidationIssue]) -> int:
    return max(0, 100 - min(40, len(warnings) * 5) - min(100, len(errors) * 20))
