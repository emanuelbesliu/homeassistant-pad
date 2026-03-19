"""Tests for the PAD Romania integration."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from custom_components.pad.api import PadApi, PadApiError
from custom_components.pad.const import (
    DOMAIN,
    API_URL,
    VALID_SERIES,
    CONF_SERIE_POLITA,
    CONF_NUMAR_POLITA,
    CONF_CNP_CUI,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    ATTR_POLICY_FOUND,
    ATTR_VALID_UNTIL,
)

# Real HTML responses from padrom.ro (confirmed March 2026)
REAL_VALID_HTML = (
    '<div class="text-center py-5">'
    '<div class="mb-5">'
    '<img class="polval" src="https://www.padrom.ro/project/views/public/img/paid/polval.png">'
    "</div>"
    '<div class="merriweather-light-14 mb-2">'
    "Poli\u021ba cu seria RA-065 \u0219i num\u0103rul 00243241690 "
    "este valabil\u0103 p\u00e2n\u0103 la data de 19-09-2026."
    "</div>"
    "</div>"
)

REAL_NOT_FOUND_HTML = (
    '<div class="text-center py-5">'
    '<div class="mb-5">'
    '<img class="polno" src="https://www.padrom.ro/project/views/public/img/paid/polno.png">'
    "</div>"
    '<div class="merriweather-light-14 mb-5">'
    "Nu a fost identificat\u0103 poli\u021ba."
    "</div>"
    '<a class="btn btn-link btn-lg" href="https://www.padrom.ro/verifica-online-pad/">'
    "Caut\u0103 din nou</a>"
    "</div>"
)


# ─── Constants tests ──────────────────────────────────────────────


class TestConstants:
    """Test the integration constants."""

    def test_domain(self):
        assert DOMAIN == "pad"

    def test_api_url(self):
        assert "padrom.ro" in API_URL

    def test_valid_series_not_empty(self):
        assert len(VALID_SERIES) > 0

    def test_valid_series_format(self):
        """All series should start with RA- or RX."""
        for serie in VALID_SERIES:
            assert serie.startswith("RA-") or serie.startswith("RX"), (
                f"Unexpected series format: {serie}"
            )

    def test_update_interval_defaults(self):
        assert MIN_UPDATE_INTERVAL < DEFAULT_UPDATE_INTERVAL < MAX_UPDATE_INTERVAL
        assert MIN_UPDATE_INTERVAL == 3600  # 1 hour
        assert DEFAULT_UPDATE_INTERVAL == 86400  # 24 hours
        assert MAX_UPDATE_INTERVAL == 604800  # 7 days


# ─── API client tests ─────────────────────────────────────────────


class TestPadApi:
    """Test the PadApi client."""

    def test_init(self):
        """Test API client initialization."""
        api = PadApi()
        assert api._session is not None
        assert "User-Agent" in api._session.headers
        assert "padrom.ro" in api._session.headers.get("Referer", "")
        api.close()

    def test_close(self):
        """Test closing the API session."""
        api = PadApi()
        api.close()
        # Should not raise

    @patch("custom_components.pad.api.requests.Session")
    def test_verify_policy_timeout(self, mock_session_cls):
        """Test timeout error handling."""
        import requests as req

        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session.post.side_effect = req.exceptions.Timeout("timeout")
        mock_session_cls.return_value = mock_session

        api = PadApi()
        api._session = mock_session

        with pytest.raises(PadApiError, match="Timeout"):
            api.verify_policy("RA-065", "00243241690", "1234567890123")

    @patch("custom_components.pad.api.requests.Session")
    def test_verify_policy_connection_error(self, mock_session_cls):
        """Test connection error handling."""
        import requests as req

        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session.post.side_effect = req.exceptions.ConnectionError("conn")
        mock_session_cls.return_value = mock_session

        api = PadApi()
        api._session = mock_session

        with pytest.raises(PadApiError, match="Connection"):
            api.verify_policy("RA-065", "00243241690", "1234567890123")

    @patch("custom_components.pad.api.requests.Session")
    def test_verify_policy_http_error(self, mock_session_cls):
        """Test HTTP error handling."""
        import requests as req

        mock_session = MagicMock()
        mock_session.headers = {}
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError(
            "403"
        )
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session

        api = PadApi()
        api._session = mock_session

        with pytest.raises(PadApiError, match="HTTP"):
            api.verify_policy("RA-065", "00243241690", "1234567890123")


# ─── Response parsing tests ───────────────────────────────────────


class TestParseResponse:
    """Test the response parsing logic with real padrom.ro HTML."""

    def _make_response(self, html, json_data=None):
        """Create a mock response object."""
        mock = MagicMock()
        mock.text = html
        if json_data is not None:
            mock.json.return_value = json_data
        else:
            mock.json.side_effect = ValueError("No JSON")
        return mock

    def test_valid_policy_real_response(self):
        """Test parsing a real valid policy response from padrom.ro."""
        api = PadApi()
        response = self._make_response(
            REAL_VALID_HTML,
            {"_c": {"response": REAL_VALID_HTML}},
        )

        result = api._parse_response(response, "RA-065", "00243241690")

        assert result[ATTR_POLICY_FOUND] is True
        assert result[ATTR_VALID_UNTIL] == "19-09-2026"
        assert result["policy_series"] == "RA-065"
        assert result["policy_number"] == "00243241690"
        assert "last_check" in result
        api.close()

    def test_not_found_real_response(self):
        """Test parsing a real not-found response from padrom.ro."""
        api = PadApi()
        response = self._make_response(
            REAL_NOT_FOUND_HTML,
            {"_c": {"response": REAL_NOT_FOUND_HTML}},
        )

        result = api._parse_response(response, "RA-065", "99999999999")

        assert result[ATTR_POLICY_FOUND] is False
        assert result["policy_series"] == "RA-065"
        assert result["policy_number"] == "99999999999"
        assert "last_check" in result
        api.close()

    def test_not_found_polno_indicator(self):
        """Test not-found detection via polno.png indicator."""
        api = PadApi()
        html = '<div><img src="polno.png"/>Nu a fost identificată polița.</div>'
        response = self._make_response(
            html,
            {"_c": {"response": html}},
        )

        result = api._parse_response(response, "RA-065", "00000000000")
        assert result[ATTR_POLICY_FOUND] is False
        api.close()

    def test_empty_response(self):
        """Test parsing an empty response."""
        api = PadApi()
        response = self._make_response("", {"_c": {"response": ""}})

        result = api._parse_response(response, "RA-065", "12345")

        assert result[ATTR_POLICY_FOUND] is False
        api.close()

    def test_valid_policy_different_date(self):
        """Test parsing a valid policy with a different date."""
        api = PadApi()
        html = (
            '<div class="merriweather-light-14 mb-2">'
            "Polița cu seria RA-002 și numărul 11111111111 "
            "este valabilă până la data de 01-01-2027."
            "</div>"
        )
        response = self._make_response(html, {"_c": {"response": html}})

        result = api._parse_response(response, "RA-002", "11111111111")

        assert result[ATTR_POLICY_FOUND] is True
        assert result[ATTR_VALID_UNTIL] == "01-01-2027"
        api.close()

    def test_raw_html_fallback(self):
        """Test parsing when response is not JSON."""
        api = PadApi()
        html = (
            '<div>Polița este valabilă până la data de 15-06-2026.</div>'
        )
        response = self._make_response(html)

        result = api._parse_response(response, "RA-065", "12345")

        assert result[ATTR_POLICY_FOUND] is True
        assert result[ATTR_VALID_UNTIL] == "15-06-2026"
        api.close()

    def test_valid_policy_no_date_extracted(self):
        """Test valid policy where date regex doesn't match."""
        api = PadApi()
        # polval.png present but no recognizable date format
        html = '<div><img class="polval" src="polval.png"/>Some text</div>'
        response = self._make_response(html, {"_c": {"response": html}})

        result = api._parse_response(response, "RA-065", "12345")

        assert result[ATTR_POLICY_FOUND] is True
        assert ATTR_VALID_UNTIL not in result
        api.close()

    def test_xf_json_structure(self):
        """Test parsing XF framework JSON with _c.response."""
        api = PadApi()
        html = (
            "Polița este valabilă până la data de 30-12-2025."
        )
        json_data = {"_c": {"response": html}}
        response = self._make_response(html, json_data)

        result = api._parse_response(response, "RA-065", "12345")

        assert result[ATTR_POLICY_FOUND] is True
        assert result[ATTR_VALID_UNTIL] == "30-12-2025"
        api.close()


# ─── Sensor helpers tests ─────────────────────────────────────────


class TestSensorHelpers:
    """Test sensor helper functions."""

    def test_parse_date_dd_dash_mm_dash_yyyy(self):
        """Test DD-MM-YYYY format (actual padrom.ro format)."""
        from custom_components.pad.sensor import _parse_date

        result = _parse_date("19-09-2026")
        assert result == datetime(2026, 9, 19)

    def test_parse_date_dd_dot_mm_dot_yyyy(self):
        from custom_components.pad.sensor import _parse_date

        result = _parse_date("01.06.2025")
        assert result == datetime(2025, 6, 1)

    def test_parse_date_slash(self):
        from custom_components.pad.sensor import _parse_date

        result = _parse_date("15/12/2025")
        assert result == datetime(2025, 12, 15)

    def test_parse_date_iso(self):
        from custom_components.pad.sensor import _parse_date

        result = _parse_date("2025-06-01")
        assert result == datetime(2025, 6, 1)

    def test_parse_date_invalid(self):
        from custom_components.pad.sensor import _parse_date

        result = _parse_date("not-a-date")
        assert result is None

    def test_parse_date_whitespace(self):
        from custom_components.pad.sensor import _parse_date

        result = _parse_date("  19-09-2026  ")
        assert result == datetime(2026, 9, 19)


# ─── Validate connection tests ────────────────────────────────────


class TestValidateConnection:
    """Test the validate_connection method."""

    @patch.object(PadApi, "verify_policy")
    def test_validate_success_found(self, mock_verify):
        """validate_connection succeeds when policy is found."""
        mock_verify.return_value = {
            "policy_found": True,
            "valid_until": "19-09-2026",
        }
        api = PadApi()
        result = api.validate_connection("RA-065", "12345", "1234567890123")
        assert result is True
        api.close()

    @patch.object(PadApi, "verify_policy")
    def test_validate_success_not_found(self, mock_verify):
        """validate_connection succeeds even when policy is not found."""
        mock_verify.return_value = {
            "policy_found": False,
        }
        api = PadApi()
        result = api.validate_connection("RA-065", "12345", "1234567890123")
        assert result is True
        api.close()

    @patch.object(PadApi, "verify_policy")
    def test_validate_none_response(self, mock_verify):
        """validate_connection raises error when response is None."""
        mock_verify.return_value = None
        api = PadApi()
        with pytest.raises(PadApiError, match="unparseable"):
            api.validate_connection("RA-065", "12345", "1234567890123")
        api.close()

    @patch.object(PadApi, "verify_policy")
    def test_validate_api_error(self, mock_verify):
        """validate_connection propagates API errors."""
        mock_verify.side_effect = PadApiError("Connection failed")
        api = PadApi()
        with pytest.raises(PadApiError, match="Connection failed"):
            api.validate_connection("RA-065", "12345", "1234567890123")
        api.close()
