<script setup lang="ts">
import MarkdownIt from "markdown-it";
//@ts-ignore
import markdownItRegexp from "markdown-it-regexp";
import { computed, inject, ref, watch } from "vue";

import { useGxUris } from "@/components/Markdown/gxuris";
import { resolveInlineDirectives } from "@/components/Markdown/Utilities/resolveInlineDirectives";
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

// Inject invocationId from parent (e.g., InvocationReport.vue)
const invocationId = inject<string | undefined>("invocationId", undefined);

const { getInvocationById, fetchInvocationById } = useInvocationStore();

// Fetch the invocation data when invocationId is available
watch(
    () => invocationId,
    async (id) => {
        if (id) {
            await fetchInvocationById({ id });
        }
    },
    { immediate: true },
);

// Get invocation data for resolution
const invocation = computed(() => (invocationId ? getInvocationById(invocationId) : undefined));

// Resolve inline directives using invocation context
const processedContent = computed(() => {
    return resolveInlineDirectives(props.content, invocation.value);
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
