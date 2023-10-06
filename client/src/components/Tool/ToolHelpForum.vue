<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCard, BCardText } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { type HelpForumPost, type HelpForumTopic } from "./helpForumServices";
import testResponse from "./testResponse.json";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const helpAvailable = computed(() => true);
const topics = ref<HelpForumTopic[]>([]);
const posts = ref<HelpForumPost[]>([]);

const root = ref(null);

onMounted(async () => {
    //const response = await search("workflows");

    topics.value = testResponse.topics;
    posts.value = testResponse.posts;
});

const displayCount = 5;

const displayedTopics = computed(() => topics.value.slice(0, displayCount - 1));
const hasMore = computed(() => topics.value.length > displayCount);

function blurbForTopic(topicId: number): string {
    const firstPost = posts.value.find((post) => post.topic_id === topicId && post.post_number === 1);
    return firstPost?.blurb ?? "no content";
}
</script>

<template>
    <div ref="root" class="tool-help-forum mt-2 mb-4">
        <Heading h2 separator bold size="sm">Help Forum</Heading>

        <p v-if="helpAvailable">
            Following questions on the <ExternalLink href="help forum link here"> Help Forum </ExternalLink> mention
            this tool:
        </p>
        <p v-else>
            There are no questions on the
            <ExternalLink href="help forum link here"> Help Forum </ExternalLink>
            about this tool.
        </p>

        <BCard v-for="topic in displayedTopics" :key="topic.id" class="mb-2">
            <Heading h3 size="sm"> {{ topic.title }} </Heading>
            <BCardText> {{ blurbForTopic(topic.id) }} </BCardText>
        </BCard>

        <div v-if="hasMore">more...</div>

        <BButton variant="primary" class="font-weight-bold" target="blank" href="help forum new question link here">
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
