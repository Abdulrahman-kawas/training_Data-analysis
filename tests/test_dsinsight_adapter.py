"""
Unit tests for dsinsight_adapter.api_response_to_multi_keyword_data.

These tests verify that the adapter correctly converts DS.API v2 JSON
responses into the existing MultiKeywordDSInsightData model, ensuring the
downstream report-generation pipeline does not need to change.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DS_INSIGHT_APP_ID", "test-app-id")

from backend.services.report.api.dsinsight_adapter import (  # noqa: E402
    api_response_to_multi_keyword_data,
)
from backend.services.report.parsers.dsinsight import (  # noqa: E402
    DSInsightData,
    MultiKeywordDSInsightData,
    RankingEntry,
    SearchVolumeEntry,
)


# ---------------------------------------------------------------------------
# Fixtures / shared test data
# ---------------------------------------------------------------------------

KEYWORDS = ["python", "django"]

VOLUME_RESPONSE = {
    "results": [
        {
            "keyword": "python",
            "date": "2024-01-01",
            "volume": 12000,
            "genderMaleRatio": 0.6,
            "genderFemaleRatio": 0.4,
            "generation10sRatio": 0.05,
            "generation20sRatio": 0.25,
            "generation30sRatio": 0.30,
            "generation40sRatio": 0.20,
            "generation50sRatio": 0.12,
            "generation60sRatio": 0.08,
            "prefecture": "13",
        },
        {
            "keyword": "python",
            "date": "2024-02-01",
            "volume": 13500,
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

RANKING_RESPONSES = {
    "python": {
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
                "generation20sRatio": 0.40,
                "generation30sRatio": 0.35,
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
    },
    "django": {
        "keyword": "django",
        "results": [
            {
                "rank": 1,
                "keyword": "python",
                "volume": 9000,
                "momVolume": 8500,
                "momRatio": 1.06,
                "yoyVolume": 7000,
                "yoyRatio": 1.29,
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Tests: return type and structure
# ---------------------------------------------------------------------------


class TestReturnType:
    def test_returns_multi_keyword_ds_insight_data(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        assert isinstance(result, MultiKeywordDSInsightData)

    def test_keywords_list_preserved(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        assert result.keywords == KEYWORDS

    def test_data_keys_match_keywords(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        assert set(result.data.keys()) == set(KEYWORDS)

    def test_each_value_is_ds_insight_data(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        for kw in KEYWORDS:
            assert isinstance(result.data[kw], DSInsightData)


# ---------------------------------------------------------------------------
# Tests: search volume mapping
# ---------------------------------------------------------------------------


class TestSearchVolumeMapping:
    def test_volume_entries_grouped_by_keyword(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        assert len(result.data["python"].search_volume) == 2
        assert len(result.data["django"].search_volume) == 1

    def test_volume_entry_fields(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        first_python_entry = result.data["python"].search_volume[0]
        assert isinstance(first_python_entry, SearchVolumeEntry)
        assert first_python_entry.date == "2024-01-01"
        assert first_python_entry.volume == 12000
        assert first_python_entry.gender_male_ratio == 0.6
        assert first_python_entry.gender_female_ratio == 0.4
        assert first_python_entry.generation_10s_ratio == 0.05
        assert first_python_entry.prefecture == "13"

    def test_optional_volume_fields_default_to_none(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        second_python_entry = result.data["python"].search_volume[1]
        assert second_python_entry.gender_male_ratio is None
        assert second_python_entry.prefecture is None

    def test_volume_cast_to_int(self):
        volume_response = {
            "results": [
                {"keyword": "python", "date": "2024-01-01", "volume": "9999"}
            ]
        }
        result = api_response_to_multi_keyword_data(
            volume_response=volume_response,
            ranking_responses={},
            keywords=["python"],
        )
        assert result.data["python"].search_volume[0].volume == 9999
        assert isinstance(result.data["python"].search_volume[0].volume, int)


# ---------------------------------------------------------------------------
# Tests: ranking mapping
# ---------------------------------------------------------------------------


class TestRankingMapping:
    def test_ranking_entries_count(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        assert len(result.data["python"].ranking) == 2
        assert len(result.data["django"].ranking) == 1

    def test_ranking_entry_fields(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        top_entry = result.data["python"].ranking[0]
        assert isinstance(top_entry, RankingEntry)
        assert top_entry.rank == 1
        assert top_entry.keyword == "django"
        assert top_entry.volume == 5000
        assert top_entry.mom_volume == 4800
        assert top_entry.mom_ratio == 1.04
        assert top_entry.yoy_volume == 3000
        assert top_entry.yoy_ratio == 1.67
        assert top_entry.gender_male_ratio == 0.55

    def test_optional_ranking_fields_default_to_none(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        second_entry = result.data["python"].ranking[1]
        assert second_entry.mom_volume is None
        assert second_entry.yoy_ratio is None

    def test_ranking_volume_cast_to_int(self):
        ranking_responses = {
            "python": {
                "keyword": "python",
                "results": [
                    {"rank": "1", "keyword": "django", "volume": "5000"}
                ],
            }
        }
        result = api_response_to_multi_keyword_data(
            volume_response={"results": []},
            ranking_responses=ranking_responses,
            keywords=["python"],
        )
        entry = result.data["python"].ranking[0]
        assert entry.rank == 1
        assert isinstance(entry.rank, int)
        assert entry.volume == 5000
        assert isinstance(entry.volume, int)


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_keywords_list(self):
        result = api_response_to_multi_keyword_data(
            volume_response={"results": []},
            ranking_responses={},
            keywords=[],
        )
        assert isinstance(result, MultiKeywordDSInsightData)
        assert result.keywords == []
        assert result.data == {}

    def test_keyword_missing_from_volume_response(self):
        result = api_response_to_multi_keyword_data(
            volume_response={"results": []},
            ranking_responses={},
            keywords=["python"],
        )
        assert result.data["python"].search_volume == []

    def test_keyword_missing_from_ranking_responses(self):
        result = api_response_to_multi_keyword_data(
            volume_response={"results": []},
            ranking_responses={},
            keywords=["python"],
        )
        assert result.data["python"].ranking == []

    def test_volume_results_for_unknown_keyword_ignored(self):
        volume_response = {
            "results": [
                {"keyword": "unknown_kw", "date": "2024-01-01", "volume": 100}
            ]
        }
        result = api_response_to_multi_keyword_data(
            volume_response=volume_response,
            ranking_responses={},
            keywords=["python"],
        )
        assert result.data["python"].search_volume == []

    def test_get_helper_returns_ds_insight_data(self):
        result = api_response_to_multi_keyword_data(
            volume_response=VOLUME_RESPONSE,
            ranking_responses=RANKING_RESPONSES,
            keywords=KEYWORDS,
        )
        assert result.get("python") is result.data["python"]

    def test_get_helper_returns_none_for_missing_keyword(self):
        result = api_response_to_multi_keyword_data(
            volume_response={"results": []},
            ranking_responses={},
            keywords=[],
        )
        assert result.get("python") is None

    def test_single_keyword(self):
        volume_response = {
            "results": [
                {"keyword": "python", "date": "2024-01-01", "volume": 12000}
            ]
        }
        ranking_responses = {
            "python": {
                "keyword": "python",
                "results": [
                    {"rank": 1, "keyword": "django", "volume": 5000}
                ],
            }
        }
        result = api_response_to_multi_keyword_data(
            volume_response=volume_response,
            ranking_responses=ranking_responses,
            keywords=["python"],
        )
        assert result.keywords == ["python"]
        assert len(result.data["python"].search_volume) == 1
        assert len(result.data["python"].ranking) == 1
