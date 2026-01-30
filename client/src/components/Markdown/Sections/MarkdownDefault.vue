<script setup lang="ts">
import MarkdownIt from "markdown-it";
//@ts-ignore
import markdownItRegexp from "markdown-it-regexp";
import { computed, ref, watch } from "vue";

import { useGxUris } from "@/components/Markdown/gxuris";
import {
    extractInvocationIds,
    resolveInlineDirectives,
} from "@/components/Markdown/Utilities/resolveInlineDirectives";
import { useInvocationStore } from "@/stores/invocationStore";

//@ts-ignore
import markdownItKatex from "./Plugins/markdown-it-katex";

const mdNewline = markdownItRegexp(/<br>/, () => {
    return "<div style='clear:both;'/><br>";
});

const md = MarkdownIt();
md.use(mdNewline);
md.use(markdownItKatex, { throwOnError: false });

const props = defineProps<{
    content: string;
}>();

const { getInvocationById, fetchInvocationById } = useInvocationStore();

// Extract invocation IDs and fetch them when content changes
const invocationIds = computed(() => extractInvocationIds(props.content));

watch(
    invocationIds,
    async (ids) => {
        for (const id of ids) {
            await fetchInvocationById({ id });
        }
    },
    { immediate: true },
);

// Resolve inline directives using fetched invocation data
const processedContent = computed(() => {
    return resolveInlineDirectives(props.content, getInvocationById);
});

const renderedContent = computed(() => md.render(processedContent.value));

const renderedMarkdownDiv = ref<HTMLDivElement>();
const { internalHelpReferences, MarkdownHelpPopovers } = useGxUris(renderedMarkdownDiv);
</script>

<template>
    <span>
        <div ref="renderedMarkdownDiv" class="text-justify" v-html="renderedContent" />
        <MarkdownHelpPopovers :elements="internalHelpReferences" />
    </span>
</template>
