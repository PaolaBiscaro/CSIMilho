from fastapi.testclient import TestClient

from app.config import get_settings
from app.data.session_store import dataset_store
from app.main import app


def multipart(package: dict[str, bytes]):
    return [("files", (name, content, "text/csv")) for name, content in package.items()]


def test_complete_package_returns_201_and_stores_dataset(presentation_package) -> None:
    dataset_store.clear()

    response = TestClient(app).post("/api/datasets", files=multipart(presentation_package))

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready_with_warnings"
    assert len(payload["fields"]) == 4
    assert len(payload["valid_pairs"]) == 2
    assert payload["available_operations"] == ["CALAGEM", "MILHO"]
    assert payload["soil"] == {
        "sample_count": 2,
        "scope": "dataset",
        "measurement_groups": ["group_1", "group_2"],
    }
    assert payload["errors"] == []
    assert payload["operation_linkage"] == {
        "assigned_rows": 8,
        "unassigned_rows": 0,
        "invalid_geometry_rows": 0,
        "ambiguous_rows": 0,
    }
    assert payload["quality_score"] == 85
    stored = dataset_store.get(payload["dataset_id"])
    assert len(stored.ndvi_observations) == 4
    assert len(stored.planting_operations) == 4
    assert len(stored.soil_samples) == 2
    assert stored.soil_samples["scope"].tolist() == ["dataset", "dataset"]
    assert "field_id" not in stored.soil_samples.columns
    assert stored.soil_metadata["measurement_groups"] == ["group_1", "group_2"]


def test_incomplete_package_returns_422_with_clear_error(presentation_package) -> None:
    presentation_package.pop("fields.csv")

    response = TestClient(app).post("/api/datasets", files=multipart(presentation_package))

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["dataset_id"] is None
    assert payload["errors"][0]["code"] == "missing_file"
    assert "fields.csv" in payload["errors"][0]["message"]


def test_package_without_soil_returns_clear_error(presentation_package) -> None:
    presentation_package.pop("soil_analysis.csv")

    response = TestClient(app).post("/api/datasets", files=multipart(presentation_package))

    assert response.status_code == 422
    payload = response.json()
    assert payload["soil"] == {
        "sample_count": 0, "scope": "dataset", "measurement_groups": []
    }
    assert any(
        issue["code"] == "missing_file" and issue["file"] == "soil_analysis.csv"
        for issue in payload["errors"]
    )


def test_missing_column_returns_422(presentation_package) -> None:
    presentation_package["fields.csv"] = b"idField,idFarm,fieldName\n1,F-1,Area\n"

    response = TestClient(app).post("/api/datasets", files=multipart(presentation_package))

    assert response.status_code == 422
    assert any(issue["code"] == "missing_column" for issue in response.json()["errors"])


def test_package_over_limit_returns_413(monkeypatch, presentation_package) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    presentation_package["fields.csv"] += b" " * (1024 * 1024)

    response = TestClient(app).post("/api/datasets", files=multipart(presentation_package))

    assert response.status_code == 413
    assert response.json()["errors"][0]["code"] == "package_too_large"
    get_settings.cache_clear()
