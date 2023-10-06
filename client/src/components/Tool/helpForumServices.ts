import { computed, Ref } from "vue";

import { useConfigStore } from "@/stores/configurationStore";

export interface HelpForumTopic {
    id: number;
    title: string;
    fancy_title: string;
    slug: string;
    posts_count: number;
    reply_count: number;
    highest_post_number: number;
    created_at: string;
    last_posted_at: string;
    bumped: boolean;
    bumped_at: string;
    archetype: unknown;
    unseen: boolean;
    pinned: boolean;
    unpinned: unknown;
    visible: boolean;
    closed: boolean;
    archived: boolean;
    bookmarked: unknown;
    liked: unknown;
    tags: string[];
    tags_descriptions: unknown;
    category_id: number;
    has_accepted_answer: boolean;
}

export interface HelpForumPost {
    id: number;
    name: string;
    username: string;
    avatar_template: string;
    created_at: string;
    like_count: number;
    blurb: string;
    post_number: number;
    topic_id: number;
}

export interface HelpForumSearchResponseData {
    posts: HelpForumPost[];
    topics: HelpForumTopic[];
    users: unknown;
    categories: unknown;
    tags: unknown;
    groups: unknown;
    grouped_search_result: unknown;
}

/**
 * Generate a url that link to the galaxy help forum to create a new topic with pre defined fields
 * @param title title of the new topic
 * @param category optional - pre defined category
 * @param tags optional - pre defined tags
 * @param body optional - pre defined body
 */
export function useCreateNewTopicUrl(
    title: Ref<string>,
    category?: Ref<string>,
    tags?: Ref<string[]>,
    body?: Ref<string>
) {
    const configStore = useConfigStore();

    const createNewTopicUrl = computed(() => {
        const url = new URL("/new-topic", configStore.config.help_forum_api_url);

        url.searchParams.append("title", encodeURIComponent(title.value));

        if (category?.value) {
            url.searchParams.append("category", category.value);
        }

        if (tags?.value) {
            url.searchParams.append("tags", tags.value.join(","));
        }

        if (body?.value) {
            url.searchParams.append("body", encodeURIComponent(body.value));
        }

        return url;
    });

    return {
        createNewTopicUrl,
    };
}
