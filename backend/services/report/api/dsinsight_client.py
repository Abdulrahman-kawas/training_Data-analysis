"""
DS.API v2 client for DS INSIGHT (Yahoo! JAPAN search data).

Authentication
--------------
Every request must include the application ID (App ID) as the
``appid`` query-string parameter.  The App ID must be stored in AWS SSM
Parameter Store under the key ``DS_INSIGHT_APP_ID`` and injected into the
Lambda function as the ``DS_INSIGHT_APP_ID`` environment variable.

API pricing (reference)
-----------------------
- Search Volume API  : ¥5 / request
- Search Ranking API : ¥3 / request
- Date Options API   : free
"""

from __future__ import annotations

import os
from typing import Any, Optional

import requests


class DSInsightAPIError(Exception):
    """Raised when the DS.API returns a non-2xx response."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"DS.API error {status_code}: {body}")


class DSInsightAPIClient:
    """Thin HTTP client for the DS.API v2 INSIGHT endpoints.

    Parameters
    ----------
    app_id:
        The DS.API application ID.  When omitted the value is read from the
        ``DS_INSIGHT_APP_ID`` environment variable.
    session:
        An optional :class:`requests.Session` to use.  Primarily useful for
        testing (pass a mock / custom session).
    """

    BASE_URL = "https://ds.yahooapis.jp/v2"

    def __init__(
        self,
        app_id: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.app_id = app_id or os.environ["DS_INSIGHT_APP_ID"]
        self._session = session or requests.Session()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_date_options(self, api_type: str = "searchvolume") -> dict[str, Any]:
        """Return the available date range for the given API type.

        This endpoint is free of charge and should be called before
        :meth:`get_search_volume` or :meth:`get_search_ranking` to confirm
        which dates are available.

        Parameters
        ----------
        api_type:
            ``"searchvolume"`` (default) or ``"searchranking"``.

        Returns
        -------
        dict
            Raw JSON response from the API, e.g.::

                {
                    "dailyStartDate": "2023-01-01",
                    "dailyEndDate":   "2024-12-31",
                    "weeklyStartDate": ...,
                    "monthlyStartDate": ...,
                }
        """
        url = f"{self.BASE_URL}/dateoptions"
        params = {"appid": self.app_id, "apiType": api_type}
        response = self._session.get(url, params=params, timeout=30)
        self._raise_for_status(response)
        return response.json()

    def get_search_volume(
        self,
        keywords: list[str],
        period: str,
        start_date: str,
        end_date: str,
        *,
        prefecture: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch search volume time series for up to 10 keywords at once.

        Parameters
        ----------
        keywords:
            List of search keywords (1–10 items).
        period:
            Aggregation period: ``"daily"``, ``"weekly"``, or ``"monthly"``.
        start_date:
            Start of the date range in ``YYYY-MM-DD`` format.
        end_date:
            End of the date range in ``YYYY-MM-DD`` format.
        prefecture:
            Optional JIS prefecture code (e.g. ``"13"`` for Tokyo).

        Returns
        -------
        dict
            Raw JSON response, e.g.::

                {
                    "results": [
                        {
                            "keyword": "python",
                            "date": "2024-01-01",
                            "volume": 12000,
                            "genderMaleRatio": 0.6,
                            ...
                        },
                        ...
                    ]
                }
        """
        if not keywords:
            raise ValueError("At least one keyword is required.")
        if len(keywords) > 10:
            raise ValueError("Search Volume API accepts at most 10 keywords per request.")

        url = f"{self.BASE_URL}/searchvolume"
        payload: dict[str, Any] = {
            "keywords": keywords,
            "period": period,
            "startDate": start_date,
            "endDate": end_date,
        }
        if prefecture is not None:
            payload["prefecture"] = prefecture

        response = self._session.post(
            url,
            json=payload,
            params={"appid": self.app_id},
            timeout=30,
        )
        self._raise_for_status(response)
        return response.json()

    def get_search_ranking(
        self,
        keyword: str,
        period: str,
        date: str,
    ) -> dict[str, Any]:
        """Fetch co-search keyword ranking for a single keyword.

        Parameters
        ----------
        keyword:
            The seed keyword whose co-search ranking you want.
        period:
            Aggregation period: ``"weekly"`` or ``"monthly"``.
        date:
            Reference date in ``YYYY-MM-DD`` format (typically the first day
            of the desired week or month).

        Returns
        -------
        dict
            Raw JSON response, e.g.::

                {
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
                            ...
                        },
                        ...
                    ]
                }
        """
        url = f"{self.BASE_URL}/searchranking"
        payload: dict[str, Any] = {
            "keyword": keyword,
            "period": period,
            "date": date,
        }
        response = self._session.post(
            url,
            json=payload,
            params={"appid": self.app_id},
            timeout=30,
        )
        self._raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if not response.ok:
            raise DSInsightAPIError(response.status_code, response.text)
