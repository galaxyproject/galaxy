import { computed, type Ref } from "vue";

import { type components } from "@/api/schema";
import { useConfigStore } from "@/stores/configurationStore";

export type HelpForumTopic = components["schemas"]["HelpForumTopic"];

export type HelpForumPost = components["schemas"]["HelpForumPost"];

export type HelpForumSearchResponse = components["schemas"]["HelpForumSearchResponse"];

/**
 * Composable for urls to the galaxy help forum
 * @param options object with options needed to create the urls
 * @returns computed url to create a new topic and computed url to link to the search page
 */
export function useHelpURLs(options: {
    title: Ref<string>;
    category?: Ref<string>;
    tags?: Ref<string[]>;
    body?: Ref<string>;
    query: Ref<string>;
}) {
    const configStore = useConfigStore();

    const createNewTopicUrl = computed(() => {
        const url = new URL("/new-topic", configStore.config.help_forum_api_url);

        const { title, category, tags, body } = options;

        url.searchParams.append("title", title.value);

        if (category?.value) {
            url.searchParams.append("category", category.value);
        }

        if (tags?.value) {
            url.searchParams.append("tags", tags.value.join(","));
        }

        if (body?.value) {
            url.searchParams.append("body", body.value);
        }

        return url;
    });

    const searchTopicUrl = computed(() => {
        const url = new URL("/search", configStore.config.help_forum_api_url);

        const { query } = options;

        url.searchParams.append("q", query.value);

        return url;
    });

    return {
        createNewTopicUrl,
        searchTopicUrl,
    };
}

/**
 * Create a url that link to the related topic in the galaxy help forum
 * @param topicId id of the topic
 * @param slug slug of the topic
 * @returns url object
 */
export function createTopicUrl(topicId: number, slug: string): URL {
    const configStore = useConfigStore();

    return new URL(`/t/${slug}/${topicId}`, configStore.config.help_forum_api_url);
}
