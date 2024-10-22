from typing import (
    Any,
    List,
    Optional,
)

from pydantic import (
    ConfigDict,
    Field,
)
from typing_extensions import Annotated

from galaxy.schema.schema import Model

# Schema manually typed from https://docs.discourse.org/
# Discourse has an OpenApi schema (https://docs.discourse.org/openapi.json)
# but at the time of writing it is mostly untyped, which makes the manually
# created types preferable.


# TODO: remove this class once we have a proper model for all temp models
class HelpTempBaseModel(Model):
    model_config = ConfigDict(extra="allow")


class HelpForumPost(HelpTempBaseModel):
    """Model for a post in the help forum."""

    id: Annotated[int, Field(description="The ID of the post.")]
    name: Annotated[Optional[str], Field(description="The name of the post.")]
    username: Annotated[Optional[str], Field(description="The username of the post author.")]
    avatar_template: Annotated[Optional[str], Field(description="The avatar template of the user.")]
    created_at: Annotated[Optional[str], Field(description="The creation date of the post.")]
    like_count: Annotated[Optional[int], Field(description="The number of likes of the post.")]
    blurb: Annotated[Optional[str], Field(description="The blurb of the post.")]
    post_number: Annotated[Optional[int], Field(description="The post number of the post.")]
    topic_id: Annotated[Optional[int], Field(description="The ID of the topic of the post.")]


class HelpForumTopic(Model):
    """Model for a topic in the help forum compatible with Discourse API."""

    id: Annotated[int, Field(description="The ID of the topic.")]
    title: Annotated[str, Field(description="The title of the topic.")]
    fancy_title: Annotated[str, Field(description="The fancy title of the topic.")]
    slug: Annotated[str, Field(description="The slug of the topic.")]
    posts_count: Annotated[int, Field(description="The number of posts in the topic.")]
    reply_count: Annotated[int, Field(description="The number of replies in the topic.")]
    highest_post_number: Annotated[int, Field(description="The highest post number in the topic.")]
    created_at: Annotated[str, Field(description="The creation date of the topic.")]
    last_posted_at: Annotated[str, Field(description="The date of the last post in the topic.")]
    bumped: Annotated[bool, Field(description="Whether the topic was bumped.")]
    bumped_at: Annotated[str, Field(description="The date of the last bump of the topic.")]
    archetype: Annotated[Any, Field(description="The archetype of the topic.")]
    unseen: Annotated[bool, Field(description="Whether the topic is unseen.")]
    pinned: Annotated[bool, Field(description="Whether the topic is pinned.")]
    unpinned: Annotated[Optional[bool], Field(default=None, description="Whether the topic is unpinned.")]
    visible: Annotated[bool, Field(description="Whether the topic is visible.")]
    closed: Annotated[bool, Field(description="Whether the topic is closed.")]
    archived: Annotated[bool, Field(description="Whether the topic is archived.")]
    bookmarked: Annotated[Optional[bool], Field(default=None, description="Whether the topic is bookmarked.")]
    liked: Annotated[Optional[bool], Field(default=None, description="Whether the topic is liked.")]
    tags: Annotated[List[str], Field(description="The tags of the topic.")]
    tags_descriptions: Annotated[
        Optional[Any], Field(default=None, description="The descriptions of the tags of the topic.")
    ]
    category_id: Annotated[int, Field(description="The ID of the category of the topic.")]
    has_accepted_answer: Annotated[bool, Field(description="Whether the topic has an accepted answer.")]


class HelpForumUser(HelpTempBaseModel):
    """Model for a user in the help forum."""

    pass


class HelpForumCategory(HelpTempBaseModel):
    """Model for a category in the help forum."""

    pass


class HelpForumTag(HelpTempBaseModel):
    """Model for a tag in the help forum."""

    pass


class HelpForumGroup(HelpTempBaseModel):
    """Model for a group in the help forum."""

    pass


class HelpForumGroupedSearchResult(HelpTempBaseModel):
    """Model for a grouped search result."""

    pass


class HelpForumSearchResponse(Model):
    """Response model for the help search API endpoint.

    This model is based on the Discourse API response for the search endpoint.
    """

    posts: Annotated[List[HelpForumPost], Field(default=None, description="The list of posts returned by the search.")]
    topics: Annotated[
        List[HelpForumTopic], Field(default=None, description="The list of topics returned by the search.")
    ]
    users: Annotated[
        Optional[List[HelpForumUser]], Field(default=None, description="The list of users returned by the search.")
    ]
    categories: Annotated[
        Optional[List[HelpForumCategory]],
        Field(default=None, description="The list of categories returned by the search."),
    ]
    tags: Annotated[
        Optional[List[HelpForumTag]], Field(default=None, description="The list of tags returned by the search.")
    ]
    groups: Annotated[
        Optional[List[HelpForumGroup]], Field(default=None, description="The list of groups returned by the search.")
    ]
    grouped_search_result: Annotated[
        Optional[HelpForumGroupedSearchResult], Field(default=None, description="The grouped search result.")
    ]
