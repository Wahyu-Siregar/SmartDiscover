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


def test_result_lifecycle_uses_existing_hidden_helper() -> None:
    main = (ROOT / "web" / "js" / "main.js").read_text(encoding="utf-8")
    render = (ROOT / "web" / "js" / "render.js").read_text(encoding="utf-8")
    warnings = (
        ROOT / "web" / "js" / "ui" / "qualityWarnings.js"
    ).read_text(encoding="utf-8")
    assert 'setHidden(results, false)' in main
    assert 'results.setAttribute("aria-busy", String(loading))' in main
    assert '$("resultsTitle")?.focus({ preventScroll: true })' in main
    assert 'setHidden($("resultsSection"), false)' in render
    assert 'clearChildren($("recommendationList"))' in main
    assert 'setState("spotifyStatus", data.status || "unknown")' in main
    assert 'getState("spotifyStatus") === "mock-mode"' in warnings
    assert 'qualityNotes?.llm_enabled === false' in warnings
    assert "demoCatalogNotice:" in I18N.read_text(encoding="utf-8")
    assert "basicMatchingNotice:" in I18N.read_text(encoding="utf-8")


def test_prompt_first_styles_keep_mobile_and_touch_contracts() -> None:
    layout = (ROOT / "web" / "css" / "layout.css").read_text(encoding="utf-8")
    forms = (
        ROOT / "web" / "css" / "components" / "forms.css"
    ).read_text(encoding="utf-8")
    buttons = (
        ROOT / "web" / "css" / "components" / "buttons.css"
    ).read_text(encoding="utf-8")
    assert ".hero__form" in layout and "max-width: 760px" in layout
    assert ".results__main" in layout and "max-width: 920px" in layout
    assert "@media (max-width: 640px)" in layout
    assert ".how-it-works" in layout
    assert ".advanced-settings" in forms
    assert "min-height: 44px" in buttons


def test_track_cards_use_native_match_details() -> None:
    cards = (ROOT / "web" / "js" / "ui" / "cards.js").read_text(encoding="utf-8")
    assert 'el("details", { class: "track-card__details" }' in cards
    assert 'el("summary", { text: tr("trackDetails") })' in cards
    assert 'class: "track-card__score"' not in cards
    assert I18N.read_text(encoding="utf-8").count("noAudioDetails:") == 2
