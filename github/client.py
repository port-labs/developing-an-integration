import asyncio
from typing import Any, AsyncGenerator, Literal

import httpx
from aiolimiter import AsyncLimiter
from loguru import logger
from port_ocean.utils import http_async_client
from port_ocean.utils.async_iterators import stream_async_iterators_tasks
from port_ocean.utils.cache import cache_iterator_result

type RepositoryType = Literal["all", "public", "private", "forks", "sources", "member"]
type PullRequestState = Literal["open", "closed", "all"]


class Endpoints:
    ORGANIZATION = "orgs/{}"
    REPOSITORY = "orgs/{}/repos"
    PULL_REQUESTS = "repos/{}/pulls"


class GitHubClient:
    REQUEST_LIMIT_AUTHENTICATED = 5000
    REQUEST_LIMIT_UNAUTHENTICATED = 60

    def __init__(
        self, base_url: str = "https://api.github.com", access_token: str | None = None
    ) -> None:
        self.base_url = base_url
        self.access_token = access_token
        self.http_client = http_async_client
        self.http_client.headers.update(self.headers)
        time_period = 60 * 60  # 1 hour in seconds
        self.rate_limiter = AsyncLimiter(
            (
                self.REQUEST_LIMIT_AUTHENTICATED
                if self.access_token
                else self.REQUEST_LIMIT_UNAUTHENTICATED
            ),
            time_period,
        )

    @property
    def headers(self) -> dict[str, str]:
        initial_headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.access_token:
            initial_headers["Authorization"] = f"Bearer {self.access_token}"

        return initial_headers

    def _get_next_page_url(self, response: httpx.Headers) -> str | None:
        link: str = response.get("Link", None)
        if not link:
            return None

        links = link.split(",")
        for link in links:
            url, rel = link.split(";")
            if "next" in rel:
                return url.strip("<> ")

        return None

    async def _send_api_request(
        self, url: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        async with self.rate_limiter:
            logger.info(f"Making request to {url} with params: {params}")
            try:
                response = await self.http_client.get(url, params=params)
                return response
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Got HTTP error when making reques to {url} with "
                    f"status code: {e.response.status_code} and response:"
                    f" {e.response.text}"
                )
                raise
            except httpx.HTTPError as e:
                logger.error(
                    f"Got HTTP error when making request to {url} with " f"error: {e}"
                )
                raise

    async def _get_paginated_data(
        self, url: str, params: dict[str, Any] | None = None
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        next_url: str | None = url

        while next_url:
            data = await self._send_api_request(next_url, params)
            response = data.json()
            yield response

            next_url = self._get_next_page_url(data.headers)

    async def get_organizations(self, organizations: list[str]) -> list[dict[str, Any]]:
        tasks = [
            self._send_api_request(
                f"{self.base_url}/{Endpoints.ORGANIZATION.format(org)}"
            )
            for org in organizations
        ]

        return [res.json() for res in await asyncio.gather(*tasks)]

    @cache_iterator_result()
    async def get_repositories(
        self, organizations: list[str], repo_type: RepositoryType
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        tasks = [
            self._get_paginated_data(
                f"{self.base_url}/{Endpoints.REPOSITORY.format(org)}",
                {"type": repo_type},
            )
            for org in organizations
        ]

        async for repositories in stream_async_iterators_tasks(*tasks):
            yield repositories

    async def get_pull_requests(
        self,
        organizations: list[str],
        repo_type: RepositoryType,
        state: PullRequestState,
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        async for repositories in self.get_repositories(organizations, repo_type):
            tasks = [
                self._get_paginated_data(
                    f"{self.base_url}/{Endpoints.PULL_REQUESTS.format(repository['full_name'])}",
                    {"state": state},
                )
                for repository in repositories
            ]

            async for pull_requests in stream_async_iterators_tasks(*tasks):
                yield pull_requests
