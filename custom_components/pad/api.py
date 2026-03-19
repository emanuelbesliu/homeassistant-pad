"""API client for PAD Romania (padrom.ro) policy verification."""

import logging
import re
from datetime import datetime
from typing import Any

import requests

from .const import API_URL

_LOGGER = logging.getLogger(__name__)

# Timeout for API requests in seconds
REQUEST_TIMEOUT = 30

# User-Agent header
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Known "not found" indicators in the response HTML
NOT_FOUND_INDICATORS = [
    "Nu a fost identificat",
    "polno.png",
    "nu a fost gasit",
    "nu exista",
]

# Regex to extract expiry date from the valid-policy sentence:
# "Polița cu seria RA-065 și numărul 00243241690 este valabilă până la data de 19-09-2026."
_RE_VALID_UNTIL = re.compile(
    r"valabil[aă]\s+p[aâ]n[aă]\s+la\s+data\s+de\s+(\d{2}-\d{2}-\d{4})"
)


class PadApiError(Exception):
    """Exception for PAD API errors."""


class PadApi:
    """Client for the PAD Romania policy verification API."""

    def __init__(self) -> None:
        """Initialize the API client."""
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.padrom.ro/pad/",
                "Origin": "https://www.padrom.ro",
            }
        )

    def verify_policy(
        self,
        serie_polita: str,
        numar_polita: str,
        cnp_cui: str,
    ) -> dict[str, Any]:
        """Verify a PAD policy via the padrom.ro AJAX API.

        Args:
            serie_polita: Policy series (e.g. 'RA-065').
            numar_polita: Policy number (11 digits, e.g. '00243241690').
            cnp_cui: CNP or CUI of insured person.

        Returns:
            dict with parsed policy data or not-found status.

        Raises:
            PadApiError: If the API request fails.
        """
        payload = {
            "seriePolita": serie_polita,
            "numarPolita": numar_polita,
            "cnpCuiAsigurat": cnp_cui,
            "_output": "ajax",
            "_isFe": "1",
            "_c": "response",
        }

        try:
            response = self._session.post(
                API_URL,
                data=payload,
                params={"_action": "verify"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as err:
            raise PadApiError(
                f"Timeout connecting to PAD API: {err}"
            ) from err
        except requests.exceptions.ConnectionError as err:
            raise PadApiError(
                f"Connection error to PAD API: {err}"
            ) from err
        except requests.exceptions.HTTPError as err:
            raise PadApiError(
                f"HTTP error from PAD API: {err}"
            ) from err
        except requests.exceptions.RequestException as err:
            raise PadApiError(
                f"Error fetching PAD data: {err}"
            ) from err

        return self._parse_response(response, serie_polita, numar_polita)

    def validate_connection(
        self,
        serie_polita: str,
        numar_polita: str,
        cnp_cui: str,
    ) -> bool:
        """Test if the API is reachable and returns a parseable response.

        Returns:
            True if the API returned a parseable response.

        Raises:
            PadApiError: If connection or parsing fails.
        """
        data = self.verify_policy(serie_polita, numar_polita, cnp_cui)
        if data is None:
            raise PadApiError("API returned unparseable response")
        return True

    def _parse_response(
        self,
        response: requests.Response,
        serie_polita: str,
        numar_polita: str,
    ) -> dict[str, Any]:
        """Parse the API response.

        The API returns JSON (XF framework) with HTML in ``_c.response``.
        The HTML is a simple div containing either:

        - **Valid**: ``polval.png`` image + sentence with expiry date
          ``"Polița cu seria X și numărul Y este valabilă până la data de DD-MM-YYYY."``
        - **Not found**: ``polno.png`` image + ``"Nu a fost identificată polița."``
        """
        result: dict[str, Any] = {
            "policy_found": False,
            "policy_series": serie_polita,
            "policy_number": numar_polita,
            "last_check": datetime.now().isoformat(),
        }

        # Extract HTML from XF JSON response
        html_content = ""
        try:
            json_data = response.json()
            if isinstance(json_data, dict):
                if "_c" in json_data and isinstance(json_data["_c"], dict):
                    html_content = json_data["_c"].get("response", "")
                elif "response" in json_data:
                    html_content = json_data["response"]
            if not html_content:
                html_content = response.text
        except (ValueError, KeyError):
            html_content = response.text

        if not html_content:
            _LOGGER.warning("PAD API returned empty response")
            return result

        # Check for "not found" indicators
        html_lower = html_content.lower()
        for indicator in NOT_FOUND_INDICATORS:
            if indicator.lower() in html_lower:
                _LOGGER.debug(
                    "PAD policy %s-%s not found (indicator: %s)",
                    serie_polita,
                    numar_polita,
                    indicator,
                )
                result["raw_response"] = html_content[:500]
                return result

        # Policy found — extract expiry date from the sentence
        result["policy_found"] = True
        match = _RE_VALID_UNTIL.search(html_content)
        if match:
            result["valid_until"] = match.group(1)
        else:
            _LOGGER.warning(
                "PAD policy found but could not extract expiry date from: %s",
                html_content[:200],
            )

        result["raw_response"] = html_content[:500]
        return result

    def close(self) -> None:
        """Close the API session."""
        self._session.close()
