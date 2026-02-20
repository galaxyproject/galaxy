<script setup lang="ts">
import { useMarkdown } from "@/composables/markdown";

import type { Message } from "./types";
import { collapsedSummary, hasArtifacts } from "./utilities";

import AnalysisSteps from "./AnalysisSteps.vue";
import ExecutedCode from "./ExecutedCode.vue";
import MessageArtifacts from "./MessageArtifacts.vue";

const props = defineProps<{
    message: Message & { collapsedHistory: NonNullable<Message["collapsedHistory"]> };
    collapsible?: boolean;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });

function escapeHtml(raw: string): string {
    // Minimal escaping for fallback rendering.
    return raw
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function safeRenderMarkdown(content: unknown): string {
    const text = typeof content === "string" ? content : String(content ?? "");
    try {
        return renderMarkdown(text);
    } catch (error) {
        console.error("Failed to render markdown for chat message:", error);
        return `<pre>${escapeHtml(text)}</pre>`;
    }
}

// TODO: Might need to handle collapsing with a ref
</script>

<template>
    <component
        :is="props.collapsible ? 'details' : 'div'"
        v-if="props.message.collapsedHistory.length"
        :class="[props.collapsible ? 'collapsed-history' : 'intermediate-history', 'mt-3']"
        :open="!props.message.isCollapsed">
        <summary v-if="props.collapsible">
            <span>{{ `Intermediate steps (${props.message.collapsedHistory.length})` }}</span>
            <span class="chip-chevron" :class="{ open: !props.message.isCollapsed }">›</span>
        </summary>

        <h6 v-else class="mb-2">{{ `Earlier steps (${props.message.collapsedHistory.length})` }}</h6>

        <div :class="[props.collapsible ? 'collapsed-entry-body card card-body mt-3' : 'intermediate-details']">
            <div
                v-for="historyMessage in props.message.collapsedHistory"
                :key="historyMessage.id"
                :class="['previous-step', props.collapsible ? 'mb-4' : 'mb-3']">
                <div class="text-muted mb-2">
                    {{ collapsedSummary(historyMessage) }}
                </div>
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
    </component>
</template>

<style scoped lang="scss">
.intermediate-details {
    summary {
        cursor: pointer;
        font-weight: 600;
    }
}

.chip-chevron {
    transition: transform 0.2s ease;
    display: inline-block;
    margin-left: 0.5rem;

    &.open {
        transform: rotate(90deg);
    }
}
</style>
