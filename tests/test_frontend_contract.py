from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "index.html"
I18N = ROOT / "web" / "js" / "i18n.js"


class MarkupProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: Counter[str] = Counter()
        self.nodes: dict[str, tuple[str, dict[str, str | None]]] = {}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr_map = dict(attrs)
        node_id = attr_map.get("id")
        if node_id:
            self.ids[node_id] += 1
            self.nodes[node_id] = (tag, attr_map)


def parse_index() -> tuple[str, MarkupProbe]:
    source = INDEX.read_text(encoding="utf-8")
    probe = MarkupProbe()
    probe.feed(source)
    return source, probe


def test_prompt_first_structure_and_unique_runtime_ids() -> None:
    source, probe = parse_index()
    required = {
        "langSwitch",
        "spotifyLoginBtn",
        "recommendForm",
        "intentInput",
        "advancedSettings",
        "targetCountInput",
        "agenticModeSelect",
        "submitBtn",
        "statusText",
        "resultsSection",
        "resultsTitle",
        "intentCard",
        "agentFlow",
        "qualityWarnings",
        "exportSlot",
        "refineSlot",
        "recommendationList",
        "agenticPanel",
        "trackDetailModal",
        "llmBadge",
        "spotifyBadge",
        "howStep1",
        "howStep2",
        "howStep3",
    }
    assert required <= probe.ids.keys()
    assert all(probe.ids[node_id] == 1 for node_id in required)
    assert probe.nodes["advancedSettings"][0] == "details"
    assert "hidden" in probe.nodes["resultsSection"][1]
    assert 'id="healthBtn"' not in source
    assert 'id="ribbonIssue"' not in source
    assert 'class="hero__dossier"' not in source


def test_primary_copy_is_plain_language_in_both_locales() -> None:
    source, _ = parse_index()
    i18n = I18N.read_text(encoding="utf-8")
    assert "Temukan musik yang cocok dengan suasanamu." in source
    assert "Cari rekomendasi" in source
    assert "Pengaturan lanjutan" in source
    for key in (
        "advancedSettings",
        "submit",
        "stageProfiler",
        "stageSearch",
        "stageRanker",
        "stagePresenter",
        "trackDetails",
        "howStep1",
        "howStep2",
        "howStep3",
    ):
        assert i18n.count(f"{key}:") == 2
