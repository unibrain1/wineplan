"""Unit tests for parse_consumed() in scripts/parse_consumed.py.

Tests cover:
- Basic field parsing from a TSV
- Sort order: ConsumeDate descending, nulls last
- Empty/missing fields produce None (not empty strings)
- TSV with only a header row returns an empty list

The conftest.py at project root adds scripts/ to sys.path.
"""

from pathlib import Path


from parse_consumed import KEEP_FIELDS, parse_consumed

# ---------------------------------------------------------------------------
# TSV helpers
# ---------------------------------------------------------------------------

CONSUMED_FIELDS = [
    "iWine",
    "Vintage",
    "Wine",
    "ConsumeDate",
    "ConsumeNote",
    "Varietal",
    "Type",
    "Country",
    "Region",
    "Appellation",
    "Producer",
]


def _write_tsv(tmp_path: Path, headers: list[str], rows: list[dict]) -> Path:
    """Write a consumed TSV file and return its Path."""
    tsv = tmp_path / "test_consumed.tsv"
    with open(tsv, "w", encoding="latin-1") as f:
        f.write("\t".join(headers) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(h, "")) for h in headers) + "\n")
    return tsv


def _consumed_row(overrides: dict | None = None) -> dict:
    """Return a dict representing a single consumed bottle with sensible defaults."""
    base = {
        "iWine": "200001",
        "Vintage": "2016",
        "Wine": "Consumed Red",
        "ConsumeDate": "2024-03-15",
        "ConsumeNote": "Nice with dinner",
        "Varietal": "Pinot Noir",
        "Type": "Red",
        "Country": "France",
        "Region": "Burgundy",
        "Appellation": "Gevrey-Chambertin",
        "Producer": "Domaine Test",
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestBasicParsing
# ---------------------------------------------------------------------------


class TestBasicParsing:
    """parse_consumed() should return a list of dicts with the expected KEEP_FIELDS keys."""

    def test_returns_list(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [_consumed_row()])
        result = parse_consumed(tsv)
        assert isinstance(result, list)

    def test_single_record_length(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [_consumed_row()])
        result = parse_consumed(tsv)
        assert len(result) == 1

    def test_multiple_records_length(self, tmp_path):
        rows = [
            _consumed_row({"iWine": "200001", "ConsumeDate": "2024-01-10"}),
            _consumed_row({"iWine": "200002", "ConsumeDate": "2024-02-20"}),
            _consumed_row({"iWine": "200003", "ConsumeDate": "2024-03-30"}),
        ]
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, rows)
        result = parse_consumed(tsv)
        assert len(result) == 3

    def test_all_keep_fields_present(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [_consumed_row()])
        record = parse_consumed(tsv)[0]
        for field in KEEP_FIELDS:
            assert field in record, f"Expected field '{field}' in parsed record"

    def test_field_values_correct(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [_consumed_row()])
        r = parse_consumed(tsv)[0]
        assert r["iWine"] == "200001"
        assert r["Vintage"] == "2016"
        assert r["Wine"] == "Consumed Red"
        assert r["ConsumeDate"] == "2024-03-15"
        assert r["ConsumeNote"] == "Nice with dinner"
        assert r["Varietal"] == "Pinot Noir"
        assert r["Type"] == "Red"
        assert r["Country"] == "France"
        assert r["Region"] == "Burgundy"
        assert r["Appellation"] == "Gevrey-Chambertin"
        assert r["Producer"] == "Domaine Test"

    def test_whitespace_stripped_from_fields(self, tmp_path):
        # Leading/trailing whitespace in TSV values should be stripped
        row = _consumed_row({"Wine": "  Spaced Wine  ", "Producer": " Test "})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["Wine"] == "Spaced Wine"
        assert r["Producer"] == "Test"

    def test_no_extra_fields_in_output(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [_consumed_row()])
        r = parse_consumed(tsv)[0]
        # Output keys should be exactly KEEP_FIELDS (no extras)
        assert set(r.keys()) == set(KEEP_FIELDS)


# ---------------------------------------------------------------------------
# TestSortOrder
# ---------------------------------------------------------------------------


class TestSortOrder:
    """Records are sorted by ConsumeDate descending (most recent first); nulls last."""

    def test_sorted_descending_by_date(self, tmp_path):
        rows = [
            _consumed_row({"iWine": "1", "ConsumeDate": "2023-06-01"}),
            _consumed_row({"iWine": "2", "ConsumeDate": "2024-12-25"}),
            _consumed_row({"iWine": "3", "ConsumeDate": "2024-01-15"}),
        ]
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, rows)
        result = parse_consumed(tsv)
        dates = [r["ConsumeDate"] for r in result]
        assert dates == ["2024-12-25", "2024-01-15", "2023-06-01"]

    def test_null_consume_date_goes_last(self, tmp_path):
        rows = [
            _consumed_row({"iWine": "1", "ConsumeDate": ""}),
            _consumed_row({"iWine": "2", "ConsumeDate": "2024-06-01"}),
            _consumed_row({"iWine": "3", "ConsumeDate": "2023-01-01"}),
        ]
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, rows)
        result = parse_consumed(tsv)
        # Last record must be the one with a null ConsumeDate
        assert result[-1]["ConsumeDate"] is None

    def test_multiple_nulls_all_go_last(self, tmp_path):
        rows = [
            _consumed_row({"iWine": "1", "ConsumeDate": ""}),
            _consumed_row({"iWine": "2", "ConsumeDate": "2024-06-01"}),
            _consumed_row({"iWine": "3", "ConsumeDate": ""}),
        ]
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, rows)
        result = parse_consumed(tsv)
        # Non-null should appear first
        assert result[0]["ConsumeDate"] == "2024-06-01"
        # Both nulls must be at the end
        null_dates = [r["ConsumeDate"] for r in result[1:]]
        assert all(d is None for d in null_dates)

    def test_all_same_date_order_stable_enough(self, tmp_path):
        # When all dates are equal the result should still have all records
        rows = [
            _consumed_row({"iWine": str(i), "ConsumeDate": "2024-06-01"})
            for i in range(5)
        ]
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, rows)
        result = parse_consumed(tsv)
        assert len(result) == 5

    def test_all_nulls_returns_all_records(self, tmp_path):
        rows = [_consumed_row({"iWine": str(i), "ConsumeDate": ""}) for i in range(3)]
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, rows)
        result = parse_consumed(tsv)
        assert len(result) == 3
        assert all(r["ConsumeDate"] is None for r in result)


# ---------------------------------------------------------------------------
# TestEmptyFields
# ---------------------------------------------------------------------------


class TestEmptyFields:
    """Empty TSV cells must be converted to None, not left as empty strings."""

    def test_empty_consume_date_is_none(self, tmp_path):
        row = _consumed_row({"ConsumeDate": ""})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["ConsumeDate"] is None

    def test_empty_consume_note_is_none(self, tmp_path):
        row = _consumed_row({"ConsumeNote": ""})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["ConsumeNote"] is None

    def test_empty_varietal_is_none(self, tmp_path):
        row = _consumed_row({"Varietal": ""})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["Varietal"] is None

    def test_empty_region_is_none(self, tmp_path):
        row = _consumed_row({"Region": ""})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["Region"] is None

    def test_empty_appellation_is_none(self, tmp_path):
        row = _consumed_row({"Appellation": ""})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["Appellation"] is None

    def test_whitespace_only_field_is_none(self, tmp_path):
        # A field with only spaces should strip to empty string then become None
        row = _consumed_row({"ConsumeNote": "   "})
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [row])
        r = parse_consumed(tsv)[0]
        assert r["ConsumeNote"] is None

    def test_missing_column_in_tsv_is_none(self, tmp_path):
        # TSV omits the ConsumeNote column entirely
        headers_without_note = [h for h in CONSUMED_FIELDS if h != "ConsumeNote"]
        row = _consumed_row()
        tsv = _write_tsv(tmp_path, headers_without_note, [row])
        r = parse_consumed(tsv)[0]
        assert r["ConsumeNote"] is None


# ---------------------------------------------------------------------------
# TestEmptyFile
# ---------------------------------------------------------------------------


class TestEmptyFile:
    """A TSV with only a header row (no data) must return an empty list."""

    def test_header_only_returns_empty_list(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [])
        result = parse_consumed(tsv)
        assert result == []

    def test_empty_result_is_a_list_not_none(self, tmp_path):
        tsv = _write_tsv(tmp_path, CONSUMED_FIELDS, [])
        result = parse_consumed(tsv)
        assert isinstance(result, list)
