"""
Adapter layer: converts DS.API v2 JSON responses into the existing
:class:`~backend.services.report.parsers.dsinsight.MultiKeywordDSInsightData`
model so that downstream report-generation code (orchestrator,
slides/organic_search.py) does not need to change.

Usage example
-------------
::

    from backend.services.report.api.dsinsight_client import DSInsightAPIClient
    from backend.services.report.api.dsinsight_adapter import api_response_to_multi_keyword_data

    client = DSInsightAPIClient()

    volume_response  = client.get_search_volume(
        keywords=["python", "django"],
        period="monthly",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )
    ranking_responses = {
        kw: client.get_search_ranking(kw, period="monthly", date="2024-12-01")
        for kw in ["python", "django"]
    }

    result = api_response_to_multi_keyword_data(
        volume_response=volume_response,
        ranking_responses=ranking_responses,
        keywords=["python", "django"],
    )
"""

from __future__ import annotations

from typing import Any

from backend.services.report.parsers.dsinsight import (
    DSInsightData,
    MultiKeywordDSInsightData,
    RankingEntry,
    SearchVolumeEntry,
)


def _parse_volume_entry(item: dict[str, Any]) -> SearchVolumeEntry:
    """Convert a single record from the Search Volume API response."""
    return SearchVolumeEntry(
        date=item["date"],
        volume=int(item["volume"]),
        gender_male_ratio=item.get("genderMaleRatio"),
        gender_female_ratio=item.get("genderFemaleRatio"),
        generation_10s_ratio=item.get("generation10sRatio"),
        generation_20s_ratio=item.get("generation20sRatio"),
        generation_30s_ratio=item.get("generation30sRatio"),
        generation_40s_ratio=item.get("generation40sRatio"),
        generation_50s_ratio=item.get("generation50sRatio"),
        generation_60s_ratio=item.get("generation60sRatio"),
        prefecture=item.get("prefecture"),
    )


def _parse_ranking_entry(item: dict[str, Any]) -> RankingEntry:
    """Convert a single record from the Search Ranking API response."""
    return RankingEntry(
        rank=int(item["rank"]),
        keyword=item["keyword"],
        volume=int(item["volume"]),
        mom_volume=_optional_int(item.get("momVolume")),
        mom_ratio=item.get("momRatio"),
        yoy_volume=_optional_int(item.get("yoyVolume")),
        yoy_ratio=item.get("yoyRatio"),
        gender_male_ratio=item.get("genderMaleRatio"),
        gender_female_ratio=item.get("genderFemaleRatio"),
        generation_10s_ratio=item.get("generation10sRatio"),
        generation_20s_ratio=item.get("generation20sRatio"),
        generation_30s_ratio=item.get("generation30sRatio"),
        generation_40s_ratio=item.get("generation40sRatio"),
        generation_50s_ratio=item.get("generation50sRatio"),
        generation_60s_ratio=item.get("generation60sRatio"),
    )


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def api_response_to_multi_keyword_data(
    volume_response: dict[str, Any],
    ranking_responses: dict[str, dict[str, Any]],
    keywords: list[str],
) -> MultiKeywordDSInsightData:
    """Convert DS.API v2 responses into :class:`MultiKeywordDSInsightData`.

    Parameters
    ----------
    volume_response:
        Raw JSON returned by :meth:`DSInsightAPIClient.get_search_volume`.
        Expected shape::

            {
                "results": [
                    {"keyword": "...", "date": "YYYY-MM-DD", "volume": N, ...},
                    ...
                ]
            }

    ranking_responses:
        Mapping of ``keyword → raw JSON`` returned by
        :meth:`DSInsightAPIClient.get_search_ranking` for each keyword.
        Expected shape for each value::

            {
                "keyword": "...",
                "results": [
                    {"rank": N, "keyword": "...", "volume": N, ...},
                    ...
                ]
            }

    keywords:
        Ordered list of keywords that were requested.  Any keyword not
        present in the API responses is included with empty lists.

    Returns
    -------
    MultiKeywordDSInsightData
        The assembled data model ready for the downstream orchestrator.
    """
    volume_by_keyword: dict[str, list[SearchVolumeEntry]] = {kw: [] for kw in keywords}

    for item in volume_response.get("results", []):
        kw = item.get("keyword")
        if kw in volume_by_keyword:
            volume_by_keyword[kw].append(_parse_volume_entry(item))

    data: dict[str, DSInsightData] = {}
    for kw in keywords:
        ranking_raw = ranking_responses.get(kw, {})
        ranking_entries = [
            _parse_ranking_entry(r)
            for r in ranking_raw.get("results", [])
        ]
        data[kw] = DSInsightData(
            keyword=kw,
            search_volume=volume_by_keyword.get(kw, []),
            ranking=ranking_entries,
        )

    return MultiKeywordDSInsightData(keywords=list(keywords), data=data)
