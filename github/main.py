from typing import cast

from client import GitHubClient
from integration import (
    GitHubOrganizationResourceConfig,
    GitHubPullRequestResourceConfig,
    GitHubRepositoryResourceConfig,
    ObjectKind,
)
from loguru import logger
from port_ocean.context.event import event
from port_ocean.context.ocean import ocean
from port_ocean.core.ocean_types import ASYNC_GENERATOR_RESYNC_TYPE


def initialize_github_client() -> GitHubClient:
    return GitHubClient(
        base_url=ocean.integration_config.get("base_url", "https://api.github.com"),
        access_token=ocean.integration_config.get("access_token"),
    )


@ocean.on_resync(ObjectKind.ORGANIZATION)
async def get_organizations(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    client = initialize_github_client()
    selector = cast(GitHubOrganizationResourceConfig, event.resource_config).selector
    logger.info(f"Retrieving organizations: {selector.organizations}")
    organizations = await client.get_organizations(selector.organizations)
    logger.info(f"Retrieved organization batch of size: {len(organizations)}")
    yield organizations


@ocean.on_resync(ObjectKind.REPOSITORY)
async def get_repositories(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    client = initialize_github_client()
    selector = cast(GitHubRepositoryResourceConfig, event.resource_config).selector
    logger.info(
        f"Retrieving {selector.type} repositories for organizations: {selector.organizations}"
    )
    async for repositories in client.get_repositories(
        selector.organizations, selector.type
    ):
        logger.info(f"Retrieved repository batch of size: {len(repositories)}")
        yield repositories


@ocean.on_resync(ObjectKind.PULL_REQUEST)
async def get_pull_requests(kind: str) -> ASYNC_GENERATOR_RESYNC_TYPE:
    client = initialize_github_client()
    selector = cast(GitHubPullRequestResourceConfig, event.resource_config).selector
    logger.info(
        f"Retrieving {selector.state} pull requests for organizations: {selector.organizations}"
    )
    async for pull_requests in client.get_pull_requests(
        selector.organizations, selector.type, selector.state
    ):
        logger.info(f"Retrieved pull request batch of size: {len(pull_requests)}")
        yield pull_requests
