import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(main.app)


def test_frontend_stack_and_scripts_are_declared() -> None:
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert {"react", "motion"} <= package["dependencies"].keys()
    assert {"build", "typecheck", "test"} <= package["scripts"].keys()


def test_dashboard_serves_built_index_or_clear_build_error() -> None:
    response = client.get("/")
    assert response.status_code in {200, 503}
    if response.status_code == 503:
        assert "npm run build" in response.text


def test_dashboard_serves_emitted_favicon() -> None:
    dashboard = client.get("/")
    if dashboard.status_code == 503:
        assert "npm run build" in dashboard.text
        return

    favicon = re.search(r'<link rel="icon"[^>]+href="([^"]+)"', dashboard.text)

    assert dashboard.status_code == 200
    assert favicon is not None
    assert favicon.group(1).startswith("/assets/")
    assert client.get(favicon.group(1)).status_code == 200


def test_dashboard_serves_index_from_frontend_build(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<main>built frontend sentinel</main>", encoding="utf-8")
    monkeypatch.setattr(main, "FRONTEND_DIST", tmp_path, raising=False)

    response = client.get("/")

    assert response.status_code == 200
    assert "built frontend sentinel" in response.text
