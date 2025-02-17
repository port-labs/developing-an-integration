from typing import Literal

from port_ocean.core.handlers.port_app_config.api import APIPortAppConfig
from port_ocean.core.handlers.port_app_config.models import (
    PortAppConfig,
    ResourceConfig,
    Selector,
)
from port_ocean.core.integrations.base import BaseIntegration
from pydantic.fields import Field


class ObjectKind:
    ORGANIZATION = "organization"
    REPOSITORY = "repository"
    PULL_REQUEST = "pull_request"


class OrganizationSelector(Selector):
    organizations: list[str] = Field(
        description="List of organizations to retrieve repositories from",
        default_factory=list,
    )


class RespositorySelector(Selector):
    organizations: list[str] = Field(
        description="List of organizations to retrieve repositories from",
        default_factory=list,
    )
    type: Literal["all", "public", "private", "forks", "sources", "member"] = Field(
        description="Type of repositories to retrieve",
        default="all",
    )


class PullRequestSelector(Selector):
    organizations: list[str] = Field(
        description="List of organizations to retrieve repositories from",
        default_factory=list,
    )
    type: Literal["all", "public", "private", "forks", "sources", "member"] = Field(
        alias="repositoryType",
        description="Type of repositories to retrieve data from",
        default="all",
    )
    state: Literal["open", "closed", "all"] = Field(
        description="State of pull requests to retrieve",
        default="open",
    )


class GitHubOranizationResourceConfig(ResourceConfig):
    selector: OrganizationSelector
    kind: Literal["organization"]


class GitHubRepositoryResourceConfig(ResourceConfig):
    selector: RespositorySelector
    kind: Literal["repository"]


class GitHubPullRequestResourceConfig(ResourceConfig):
    selector: PullRequestSelector
    kind: Literal["pull_request"]


class GitHubPortAppConfig(PortAppConfig):
    resources: list[
        GitHubOranizationResourceConfig
        | GitHubRepositoryResourceConfig
        | GitHubPullRequestResourceConfig
        | ResourceConfig
    ] = Field(default_factory=list)


class GitHubIntegration(BaseIntegration):
    class AppConfigHandlerClass(APIPortAppConfig):
        CONFIG_CLASS = GitHubPortAppConfig
