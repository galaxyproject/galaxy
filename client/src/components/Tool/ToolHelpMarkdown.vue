<script setup lang="ts">
import { computed, ref } from "vue";

import { useGxUris } from "@/components/Markdown/gxuris";
import { markup } from "@/components/ObjectStore/configurationMarkdown";
import { useFormattedToolHelp } from "@/composables/formattedToolHelp";

const props = defineProps<{
    content: string;
}>();

const markdownHtml = computed(() => markup(props.content ?? "", false));
// correct links and header information... this should work the same between rst and
// markdown entirely I think.
const { formattedContent } = useFormattedToolHelp(markdownHtml);

const helpHtml = ref<HTMLDivElement>();

const { internalHelpReferences, MarkdownHelpPopovers } = useGxUris(helpHtml);
</script>

<template>
    <span>
        <!-- Disable v-html warning because we allow markdown generated HTML
            in various places in the Galaxy interface. Raw HTML is not allowed
            here because admin = false in the call to markup.
        -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div ref="helpHtml" v-html="formattedContent" />
        <MarkdownHelpPopovers :elements="internalHelpReferences" />
    </span>
</template>
