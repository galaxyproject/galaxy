<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCard } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { useConfigStore } from "@/stores/configurationStore";
import { getShortToolId } from "@/utils/tool";

import { createTopicUrl, type HelpForumPost, type HelpForumTopic, useHelpURLs } from "./helpForumUrls";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const props = defineProps<{
    toolId: string;
    toolName: string;
}>();

const toolHelpTag = "tool-help";

const topics = ref<HelpForumTopic[]>([]);
const posts = ref<HelpForumPost[]>([]);
const helpAvailable = computed(() => topics.value.length > 0);

const root = ref(null);

const shortToolId = computed(() => getShortToolId(props.toolId));
const query = computed(() => `tags:${shortToolId.value}+${toolHelpTag} status:solved`);

onMounted(async () => {
    const { data, error } = await GalaxyApi().GET("/api/help/forum/search", {
        params: {
            query: { query: query.value },
        },
    });
    if (error) {
        console.error("Error fetching help forum data", error);
    }

    topics.value = data?.topics ?? [];
    posts.value = data?.posts ?? [];
});

const displayCount = 5;

const displayedTopics = computed(() => topics.value.slice(0, displayCount - 1));
const hasMore = computed(() => topics.value.length > displayCount);
function blurbForTopic(topicId: number): string {
    const firstPost = posts.value.find((post) => post.topic_id === topicId);
    return firstPost?.blurb ?? "无内容";
}

const { createNewTopicUrl, searchTopicUrl } = useHelpURLs({
    title: computed(() => props.toolName),
    tags: computed(() => [shortToolId.value, toolHelpTag]),
    query,
});

const configStore = useConfigStore();
</script>

<template>
    <div ref="root" class="tool-help-forum mt-2 mb-4">
        <Heading h2 separator bold size="sm">帮助论坛</Heading>

        <p v-if="helpAvailable">
            以下是在
            <ExternalLink :href="configStore.config.help_forum_api_url">帮助论坛</ExternalLink>上可能与
            此工具相关的问题：
        </p>
        <p v-else>
            在
            <ExternalLink :href="configStore.config.help_forum_api_url">帮助论坛</ExternalLink>
            上没有关于此工具的问题。
        </p>

        <BCard v-for="topic in displayedTopics" :key="topic.id" class="mb-2">
            <ExternalLink :href="createTopicUrl(topic.id, topic.slug).href">
                <Heading h3 inline size="sm"> {{ topic.title }} </Heading>
            </ExternalLink>
            <p class="mb-0 mt-2">{{ blurbForTopic(topic.id) }}</p>
        </BCard>

        <a v-if="hasMore" :href="searchTopicUrl.href" target="_blank" class="d-block mb-2">显示全部...</a>

        <BButton variant="primary" class="font-weight-bold" target="blank" :href="createNewTopicUrl.href">
            <FontAwesomeIcon :icon="['gxd', 'galaxyLogo']" /> 提出新问题
        </BButton>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.tool-help-forum {
    --fa-secondary-color: #{$brand-toggle};
    --fa-secondary-opacity: 1;
}
</style>
