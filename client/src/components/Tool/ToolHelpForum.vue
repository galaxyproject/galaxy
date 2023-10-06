<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCard, BCardText } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { fetcher } from "@/schema";
import { useConfigStore } from "@/stores/configurationStore";

import { type HelpForumPost, type HelpForumTopic, useCreateNewTopicUrl } from "./helpForumServices";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const props = defineProps<{
    toolId: string;
    toolName: string;
}>();

const helpFetcher = fetcher.path("/api/help/search").method("get").create();

const topics = ref<HelpForumTopic[]>([]);
const posts = ref<HelpForumPost[]>([]);
const helpAvailable = computed(() => topics.value.length > 0);

const root = ref(null);

onMounted(async () => {
    const response = await helpFetcher({ query: "workflows" });
    //const response = await search("workflows");

    const data = response.data;

    topics.value = data.topics as HelpForumTopic[];
    posts.value = data.posts as unknown as HelpForumPost[];
});

const displayCount = 5;

const displayedTopics = computed(() => topics.value.slice(0, displayCount - 1));
const hasMore = computed(() => topics.value.length > displayCount);

function blurbForTopic(topicId: number): string {
    const firstPost = posts.value.find((post) => post.topic_id === topicId && post.post_number === 1);
    return firstPost?.blurb ?? "no content";
}

const { createNewTopicUrl } = useCreateNewTopicUrl(
    computed(() => props.toolName),
    undefined,
    computed(() => [props.toolId])
);

const configStore = useConfigStore();
</script>

<template>
    <div ref="root" class="tool-help-forum mt-2 mb-4">
        <Heading h2 separator bold size="sm">Help Forum</Heading>

        <p v-if="helpAvailable">
            Following questions on the
            <ExternalLink :href="configStore.config.help_forum_api_url"> Help Forum </ExternalLink> mention this tool:
        </p>
        <p v-else>
            There are no questions on the
            <ExternalLink :href="configStore.config.help_forum_api_url"> Help Forum </ExternalLink>
            about this tool.
        </p>

        <BCard v-for="topic in displayedTopics" :key="topic.id" class="mb-2">
            <Heading h3 size="sm"> {{ topic.title }} </Heading>
            <BCardText> {{ blurbForTopic(topic.id) }} </BCardText>
        </BCard>

        <div v-if="hasMore">more...</div>

        <BButton variant="primary" class="font-weight-bold" target="blank" :href="createNewTopicUrl.href">
            <FontAwesomeIcon :icon="['gxd', 'galaxyLogo']" /> Ask a new question
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
