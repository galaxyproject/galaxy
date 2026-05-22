<script setup lang="ts">
/**
 * Mode 1: Full Replacement diff view.
 * Shows a unified line-level diff between the original and proposed content,
 * with Accept/Reject buttons.
 */
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import { computeLineDiff, diffStats } from "./sectionDiffUtils";

const props = defineProps<{
    original: string;
    proposed: string;
    stale?: boolean;
}>();

const emit = defineEmits<{
    (e: "accept"): void;
    (e: "reject"): void;
}>();

const changes = computed(() => computeLineDiff(props.original, props.proposed));
const stats = computed(() => diffStats(changes.value));
</script>

<template>
    <div class="proposal-diff-view" data-description="proposal diff view">
        <div class="diff-header d-flex align-items-center justify-content-between p-2">
            <span class="diff-stats">
                <span class="text-success">+{{ stats.additions }}</span>
                <span class="mx-1">/</span>
                <span class="text-danger">-{{ stats.deletions }}</span>
                lines
            </span>
            <span
                class="diff-actions"
                :title="stale ? 'Document has changed and this suggestion no longer applies.' : undefined">
                <BButton
                    variant="success"
                    size="sm"
                    :disabled="stale"
                    data-description="accept proposal"
                    @click="emit('accept')">
                    <FontAwesomeIcon :icon="faCheck" />
                    Accept
                </BButton>
                <BButton
                    variant="outline-danger"
                    size="sm"
                    class="ml-1"
                    :disabled="stale"
                    data-description="reject proposal"
                    @click="emit('reject')">
                    <FontAwesomeIcon :icon="faTimes" />
                    Reject
                </BButton>
            </span>
        </div>
        <div class="diff-content">
            <div v-for="(change, idx) in changes" :key="idx" class="diff-block">
                <pre
                    v-for="(line, li) in change.value.split('\n').slice(0, -1)"
                    :key="`${idx}-${li}`"
                    :class="{
                        'diff-line': true,
                        'diff-added': change.added,
                        'diff-removed': change.removed,
                        'diff-context': !change.added && !change.removed,
                    }"
                    >{{ (change.added ? "+ " : change.removed ? "- " : "  ") + line }}</pre
                >
            </div>
        </div>
    </div>
</template>

<style scoped>
.proposal-diff-view {
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 4px;
    margin: 0.5rem 0;
    font-size: 0.85rem;
}

.diff-header {
    background: var(--panel-header-bg, #f8f9fa);
    border-bottom: 1px solid var(--border-color, #dee2e6);
}

.diff-content {
    max-height: 400px;
    overflow: auto;
    padding: 0;
}

.diff-line {
    margin: 0;
    padding: 1px 8px;
    font-family: monospace;
    font-size: 0.8rem;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.4;
}

.diff-added {
    background-color: rgba(40, 167, 69, 0.15);
    color: #1e7e34;
}

.diff-removed {
    background-color: rgba(220, 53, 69, 0.15);
    color: #bd2130;
}

.diff-context {
    color: var(--text-muted, #6c757d);
}
</style>
