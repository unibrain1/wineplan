"""Tests for enrich_menu.py — prompt building, JSON extraction, cache."""

import json


from enrich_menu import build_enrichment_prompt, extract_json, load_cache, text_hash


class TestTextHash:
    def test_deterministic(self):
        assert text_hash("Grilled chicken") == text_hash("Grilled chicken")

    def test_case_insensitive(self):
        assert text_hash("Grilled Chicken") == text_hash("grilled chicken")

    def test_strips_whitespace(self):
        assert text_hash("  chicken  ") == text_hash("chicken")

    def test_different_text_different_hash(self):
        assert text_hash("chicken") != text_hash("beef")

    def test_returns_16_chars(self):
        assert len(text_hash("anything")) == 16


class TestBuildEnrichmentPrompt:
    def test_includes_all_entries(self):
        entries = [
            {"meal": "Grilled chicken"},
            {"meal": "Pasta primavera"},
        ]
        prompt = build_enrichment_prompt(entries)
        assert "Grilled chicken" in prompt
        assert "Pasta primavera" in prompt

    def test_entries_are_indexed(self):
        entries = [{"meal": "Steak"}, {"meal": "Fish"}]
        prompt = build_enrichment_prompt(entries)
        assert '0: "Steak"' in prompt
        assert '1: "Fish"' in prompt

    def test_mentions_required_fields(self):
        prompt = build_enrichment_prompt([{"meal": "test"}])
        assert "protein" in prompt
        assert "preparation" in prompt
        assert "richness" in prompt
        assert "spice_heat" in prompt
        assert "pairing_priorities" in prompt


class TestExtractJson:
    def test_extracts_json_from_text(self):
        text = 'Here is the result: {"0": {"protein": "chicken"}} done.'
        result = extract_json(text)
        assert result == {"0": {"protein": "chicken"}}

    def test_handles_no_json(self):
        assert extract_json("no json here") == {}

    def test_handles_invalid_json(self):
        assert extract_json("{invalid: json}") == {}

    def test_handles_nested_json(self):
        text = '{"0": {"protein": "pork", "sides": ["kale", "potatoes"]}}'
        result = extract_json(text)
        assert result["0"]["sides"] == ["kale", "potatoes"]


class TestLoadCache:
    def test_missing_file_returns_empty(self, tmp_path):
        assert load_cache(tmp_path / "nonexistent.json") == {}

    def test_empty_file_returns_empty(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("")
        assert load_cache(p) == {}

    def test_valid_cache(self, tmp_path):
        p = tmp_path / "cache.json"
        data = {"abc123": {"protein": "chicken"}}
        p.write_text(json.dumps(data))
        assert load_cache(p) == data

    def test_invalid_json_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{bad")
        assert load_cache(p) == {}
