<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCard, BCardText } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { type HelpForumTopic } from "./helpForumServices";
import testResponse from "./testResponse.json";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const helpAvailable = computed(() => true);
const topics = ref<HelpForumTopic[]>([]);

const root = ref(null);

onMounted(async () => {
    //const response = await search("workflows");

    topics.value = testResponse.topics;
});
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

        <BCard v-for="topic in topics" :key="topic.id">
            <template v-slot:header>
                <Heading h3 inline size="sm">{{ topic.title }}</Heading>
            </template>
            <BCardText> hello world </BCardText>
        </BCard>

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
