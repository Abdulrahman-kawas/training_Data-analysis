"""
Data models for DS INSIGHT (Yahoo! JAPAN search data).

These models are shared between the CSV-based parsers (legacy) and the
DS.API v2 integration (dsinsight_client / dsinsight_adapter).  Keeping the
models here ensures that downstream report-generation logic (orchestrator,
slides/organic_search.py) does not need to change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchVolumeEntry:
    """A single data point in a keyword's search-volume time series."""

    date: str
    volume: int
    gender_male_ratio: Optional[float] = None
    gender_female_ratio: Optional[float] = None
    generation_10s_ratio: Optional[float] = None
    generation_20s_ratio: Optional[float] = None
    generation_30s_ratio: Optional[float] = None
    generation_40s_ratio: Optional[float] = None
    generation_50s_ratio: Optional[float] = None
    generation_60s_ratio: Optional[float] = None
    prefecture: Optional[str] = None


@dataclass
class RankingEntry:
    """A single row in the co-search keyword ranking."""

    rank: int
    keyword: str
    volume: int
    mom_volume: Optional[int] = None
    mom_ratio: Optional[float] = None
    yoy_volume: Optional[int] = None
    yoy_ratio: Optional[float] = None
    gender_male_ratio: Optional[float] = None
    gender_female_ratio: Optional[float] = None
    generation_10s_ratio: Optional[float] = None
    generation_20s_ratio: Optional[float] = None
    generation_30s_ratio: Optional[float] = None
    generation_40s_ratio: Optional[float] = None
    generation_50s_ratio: Optional[float] = None
    generation_60s_ratio: Optional[float] = None


@dataclass
class DSInsightData:
    """DS INSIGHT data for a single keyword."""

    keyword: str
    search_volume: list[SearchVolumeEntry] = field(default_factory=list)
    ranking: list[RankingEntry] = field(default_factory=list)


@dataclass
class MultiKeywordDSInsightData:
    """DS INSIGHT data for one or more keywords."""

    keywords: list[str] = field(default_factory=list)
    data: dict[str, DSInsightData] = field(default_factory=dict)

    def get(self, keyword: str) -> Optional[DSInsightData]:
        return self.data.get(keyword)
