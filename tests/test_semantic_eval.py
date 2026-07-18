from evals.run_eval import _lyrical_intent_recall


def test_lyrical_intent_recall_tracks_requested_meaning_terms() -> None:
    intent = "lagu tentang memaafkan diri setelah gagal"

    assert _lyrical_intent_recall(["memaafkan", "gagal"], intent) == 1.0
    assert _lyrical_intent_recall(["memaafkan", "bangkit"], intent) == 0.5
    assert _lyrical_intent_recall([], intent) == 1.0
