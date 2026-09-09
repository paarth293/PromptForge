from backend.app.services.seed_corpus_service import SeedCorpusService, get_seed_corpus_service


def test_seed_corpus_loaded_successfully():
    service = get_seed_corpus_service()
    seeds = service.get_all_seeds()

    # Step 34 requires at least 15–20 concrete, categorized attack examples
    assert len(seeds) >= 20

    for item in seeds:
        assert item["attack_id"].startswith("SEED-")
        assert item["category"] in [
            "prompt_injection",
            "system_extraction",
            "tool_abuse",
            "social_engineering",
            "multilingual_evasion"
        ]
        assert item["difficulty"] in ["trivial", "moderate", "hard"]
        assert len(item["attack_pattern"]) > 20
        assert len(item["technique"]) > 0
        assert len(item["target_surface"]) > 0


def test_seed_corpus_category_distribution():
    service = SeedCorpusService()
    counts = service.get_category_counts()

    expected_categories = [
        "prompt_injection",
        "system_extraction",
        "tool_abuse",
        "social_engineering",
        "multilingual_evasion"
    ]

    for cat in expected_categories:
        assert cat in counts
        assert counts[cat] >= 3  # At least 3 per category for diverse seeding


def test_seed_corpus_difficulty_filtering():
    service = SeedCorpusService()
    diff_counts = service.get_difficulty_counts()

    assert "trivial" in diff_counts and diff_counts["trivial"] >= 3
    assert "moderate" in diff_counts and diff_counts["moderate"] >= 5
    assert "hard" in diff_counts and diff_counts["hard"] >= 3

    # Test sampling helper
    samples = service.get_sample_seeds(count=4, category="tool_abuse")
    assert len(samples) == 4
    assert all(s["category"] == "tool_abuse" for s in samples)
