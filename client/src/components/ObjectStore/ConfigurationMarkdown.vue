<script setup lang="ts">
import { computed } from "vue";

import { markup } from "./configurationMarkdown";

interface Props {
    markdown: string;
    admin: boolean; // was the configuration specified by an admin
}
const props = defineProps<Props>();
const markdownHtml = computed(() => markup(props.markdown ?? "", props.admin));
</script>
<template>
    <!-- Disable v-html warning because we allow markdown generated HTML
         in various places in the Galaxy interface. Raw HTML will be
         excluded from markdown for all user generated content.
    -->
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-html="markdownHtml" />
</template>
