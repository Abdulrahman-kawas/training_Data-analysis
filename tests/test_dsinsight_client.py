"""
Unit tests for DSInsightAPIClient.

All HTTP calls are intercepted by the ``responses`` library so no real
network requests are made during testing.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

APP_ID = "test-app-id"

DATE_OPTIONS_RESPONSE = {
    "dailyStartDate": "2023-01-01",
    "dailyEndDate": "2024-12-31",
    "weeklyStartDate": "2023-01-02",
    "weeklyEndDate": "2024-12-30",
    "monthlyStartDate": "2023-01-01",
    "monthlyEndDate": "2024-12-01",
}

VOLUME_RESPONSE = {
    "results": [
        {
            "keyword": "python",
            "date": "2024-01-01",
            "volume": 12000,
            "genderMaleRatio": 0.6,
            "genderFemaleRatio": 0.4,
        },
        {
            "keyword": "django",
            "date": "2024-01-01",
            "volume": 4500,
            "genderMaleRatio": 0.65,
            "genderFemaleRatio": 0.35,
        },
    ]
}

RANKING_RESPONSE = {
    "keyword": "python",
    "results": [
        {
            "rank": 1,
            "keyword": "django",
            "volume": 5000,
            "momVolume": 4800,
            "momRatio": 1.04,
            "yoyVolume": 3000,
            "yoyRatio": 1.67,
            "genderMaleRatio": 0.55,
            "genderFemaleRatio": 0.45,
        },
        {
            "rank": 2,
            "keyword": "flask",
            "volume": 3000,
            "momVolume": None,
            "momRatio": None,
            "yoyVolume": None,
            "yoyRatio": None,
        },
    ],
}


def _make_mock_response(body: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.ok = status_code < 400
    mock.status_code = status_code
    mock.text = json.dumps(body)
    mock.json.return_value = body
    return mock


# ---------------------------------------------------------------------------
# Import under test (after env var is set)
# ---------------------------------------------------------------------------

os.environ.setdefault("DS_INSIGHT_APP_ID", APP_ID)

from backend.services.report.api.dsinsight_client import (  # noqa: E402
    DSInsightAPIClient,
    DSInsightAPIError,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDSInsightAPIClientInit:
    def test_reads_app_id_from_env(self):
        with patch.dict(os.environ, {"DS_INSIGHT_APP_ID": "env-app-id"}):
            client = DSInsightAPIClient()
        assert client.app_id == "env-app-id"

    def test_explicit_app_id_overrides_env(self):
        client = DSInsightAPIClient(app_id="explicit-id")
        assert client.app_id == "explicit-id"

    def test_missing_app_id_raises(self):
        env = {k: v for k, v in os.environ.items() if k != "DS_INSIGHT_APP_ID"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(KeyError):
                DSInsightAPIClient()


class TestGetDateOptions:
    def test_returns_parsed_json(self):
        mock_session = MagicMock()
        mock_session.get.return_value = _make_mock_response(DATE_OPTIONS_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        result = client.get_date_options()

        assert result == DATE_OPTIONS_RESPONSE

    def test_passes_appid_and_api_type(self):
        mock_session = MagicMock()
        mock_session.get.return_value = _make_mock_response(DATE_OPTIONS_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        client.get_date_options(api_type="searchranking")

        _args, kwargs = mock_session.get.call_args
        assert kwargs["params"]["appid"] == APP_ID
        assert kwargs["params"]["apiType"] == "searchranking"

    def test_raises_on_error_status(self):
        mock_session = MagicMock()
        mock_session.get.return_value = _make_mock_response({"error": "bad"}, 401)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        with pytest.raises(DSInsightAPIError) as exc_info:
            client.get_date_options()

        assert exc_info.value.status_code == 401


class TestGetSearchVolume:
    def test_returns_parsed_json(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response(VOLUME_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        result = client.get_search_volume(
            keywords=["python", "django"],
            period="monthly",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        assert result == VOLUME_RESPONSE

    def test_payload_contains_all_params(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response(VOLUME_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        client.get_search_volume(
            keywords=["python"],
            period="daily",
            start_date="2024-01-01",
            end_date="2024-03-31",
            prefecture="13",
        )

        _args, kwargs = mock_session.post.call_args
        payload = kwargs["json"]
        assert payload["keywords"] == ["python"]
        assert payload["period"] == "daily"
        assert payload["startDate"] == "2024-01-01"
        assert payload["endDate"] == "2024-03-31"
        assert payload["prefecture"] == "13"

    def test_prefecture_omitted_when_none(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response(VOLUME_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        client.get_search_volume(
            keywords=["python"],
            period="monthly",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        _args, kwargs = mock_session.post.call_args
        assert "prefecture" not in kwargs["json"]

    def test_empty_keywords_raises(self):
        client = DSInsightAPIClient(app_id=APP_ID)
        with pytest.raises(ValueError, match="At least one keyword"):
            client.get_search_volume(
                keywords=[],
                period="monthly",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

    def test_too_many_keywords_raises(self):
        client = DSInsightAPIClient(app_id=APP_ID)
        with pytest.raises(ValueError, match="at most 10"):
            client.get_search_volume(
                keywords=[f"kw{i}" for i in range(11)],
                period="monthly",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

    def test_raises_on_error_status(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response({"error": "forbidden"}, 403)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        with pytest.raises(DSInsightAPIError) as exc_info:
            client.get_search_volume(
                keywords=["python"],
                period="monthly",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )
        assert exc_info.value.status_code == 403


class TestGetSearchRanking:
    def test_returns_parsed_json(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response(RANKING_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        result = client.get_search_ranking(
            keyword="python", period="monthly", date="2024-12-01"
        )

        assert result == RANKING_RESPONSE

    def test_payload_structure(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response(RANKING_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        client.get_search_ranking(keyword="python", period="weekly", date="2024-12-02")

        _args, kwargs = mock_session.post.call_args
        payload = kwargs["json"]
        assert payload == {"keyword": "python", "period": "weekly", "date": "2024-12-02"}

    def test_appid_in_query_params(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response(RANKING_RESPONSE)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        client.get_search_ranking(keyword="python", period="monthly", date="2024-12-01")

        _args, kwargs = mock_session.post.call_args
        assert kwargs["params"]["appid"] == APP_ID

    def test_raises_on_error_status(self):
        mock_session = MagicMock()
        mock_session.post.return_value = _make_mock_response({"error": "not found"}, 404)

        client = DSInsightAPIClient(app_id=APP_ID, session=mock_session)
        with pytest.raises(DSInsightAPIError):
            client.get_search_ranking(
                keyword="python", period="monthly", date="2024-12-01"
            )


class TestDSInsightAPIError:
    def test_message_contains_status_and_body(self):
        err = DSInsightAPIError(500, "Internal Server Error")
        assert "500" in str(err)
        assert "Internal Server Error" in str(err)

    def test_attributes(self):
        err = DSInsightAPIError(429, "Rate limit exceeded")
        assert err.status_code == 429
        assert err.body == "Rate limit exceeded"
