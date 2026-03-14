<script setup lang="ts">
import { ref } from "vue";

import { useMarkdown } from "@/composables/markdown";

import type { ChatMessage } from "./types";
import { escapeHtml, hasArtifacts } from "./utilities";

import AnalysisSteps from "./AnalysisSteps.vue";
import ExecutedCode from "./ExecutedCode.vue";
import MessageArtifacts from "./MessageArtifacts.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    message: ChatMessage & { collapsedHistory: NonNullable<ChatMessage["collapsedHistory"]> };
    collapsible?: boolean;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
function safeRenderMarkdown(content: unknown): string {
    const text = typeof content === "string" ? content : String(content ?? "");
    try {
        return renderMarkdown(text);
    } catch (error) {
        console.error("Failed to render markdown for chat message:", error);
        return `<pre>${escapeHtml(text)}</pre>`;
    }
}

const toggled = ref(props.message.isCollapsed ?? false);
</script>

<template>
    <div
        v-if="props.message.collapsedHistory.length"
        :class="[props.collapsible ? 'collapsed-history' : 'intermediate-history', 'mt-3']">
        <Heading
            v-if="props.collapsible"
            h4
            size="sm"
            separator
            :collapse="toggled ? 'closed' : 'open'"
            @click="toggled = !toggled">
            {{ `Intermediate steps (${props.message.collapsedHistory.length})` }}
        </Heading>

        <Heading v-else h6 size="sm" class="mb-2" separator>
            {{ `Earlier steps (${props.message.collapsedHistory.length})` }}
        </Heading>

        <div
            v-if="!props.collapsible || !toggled"
            :class="[props.collapsible ? 'collapsed-entry-body card card-body mt-3' : '']">
            <div
                v-for="historyMessage in props.message.collapsedHistory"
                :key="historyMessage.id"
                :class="['previous-step', props.collapsible ? 'mb-4' : 'mb-3']">
                <div class="message-content">
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <div v-html="safeRenderMarkdown(historyMessage.content)" />

                    <MessageArtifacts
                        v-if="hasArtifacts(historyMessage)"
                        :message="historyMessage"
                        :class="props.collapsible ? 'mt-2' : ''" />

                    <ExecutedCode
                        v-if="historyMessage.agentResponse?.metadata?.executed_task?.code"
                        :metadata="historyMessage.agentResponse?.metadata"
                        class="mt-2" />
                </div>

                <AnalysisSteps
                    v-if="historyMessage.analysisSteps?.length"
                    class="mt-2"
                    :steps="historyMessage.analysisSteps" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.collapsed-history {
    border: 1px solid #dfe3e6;
    border-radius: 8px;
    background: #f7f8fa;
    padding: 0.25rem 0.75rem;

    .collapsed-entry-body {
        background: #fff;
    }
}
</style>
