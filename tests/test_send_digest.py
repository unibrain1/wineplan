"""Tests for send_digest.py — email building and idempotency."""

from send_digest import already_sent_today, build_email, mark_sent


class TestBuildEmail:
    def test_subject_includes_wine_name(self):
        digest = {
            "wine": {"vintage": "2020", "name": "Dion Vineyard Pinot Noir"},
        }
        msg = build_email(digest, "<html>body</html>", "from@test.com", ["to@test.com"])
        assert "Dion Vineyard Pinot Noir" in msg["Subject"]
        assert "2020" in msg["Subject"]

    def test_subject_fallback_when_no_wine(self):
        msg = build_email(
            {"wine": None}, "<html>body</html>", "from@test.com", ["to@test.com"]
        )
        assert "The Sommelier" in msg["Subject"]

    def test_recipients_in_header(self):
        msg = build_email(
            {"wine": None},
            "<html></html>",
            "from@test.com",
            ["a@test.com", "b@test.com"],
        )
        assert "a@test.com" in msg["To"]
        assert "b@test.com" in msg["To"]

    def test_html_content_type(self):
        msg = build_email(
            {"wine": None}, "<html>test</html>", "from@test.com", ["to@test.com"]
        )
        payload = msg.get_payload()
        assert len(payload) == 1
        assert payload[0].get_content_type() == "text/html"


class TestIdempotency:
    def test_not_sent_when_no_state_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("send_digest.STATE_FILE", tmp_path / "state.txt")
        assert already_sent_today() is False

    def test_sent_today_returns_true(self, tmp_path, monkeypatch):
        from datetime import date

        state = tmp_path / "state.txt"
        state.write_text(date.today().isoformat())
        monkeypatch.setattr("send_digest.STATE_FILE", state)
        assert already_sent_today() is True

    def test_sent_yesterday_returns_false(self, tmp_path, monkeypatch):
        from datetime import date, timedelta

        state = tmp_path / "state.txt"
        state.write_text((date.today() - timedelta(days=1)).isoformat())
        monkeypatch.setattr("send_digest.STATE_FILE", state)
        assert already_sent_today() is False

    def test_mark_sent_creates_file(self, tmp_path, monkeypatch):
        from datetime import date

        state = tmp_path / "state.txt"
        monkeypatch.setattr("send_digest.STATE_FILE", state)
        mark_sent()
        assert state.exists()
        assert state.read_text() == date.today().isoformat()
