<script setup lang="ts">
import { faArrowLeft, faExchangeAlt, faEye, faSpinner, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import type { PageRevisionDetails } from "@/api/pages";

import { computeLineDiff, diffStats } from "./sectionDiffUtils";

import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    revision: PageRevisionDetails;
    currentContent: string;
    viewMode: "preview" | "changes";
    isReverting: boolean;
}>();

const emit = defineEmits<{
    (e: "back"): void;
    (e: "restore", revisionId: string): void;
    (e: "update:viewMode", mode: "preview" | "changes"): void;
}>();

const markdownConfig = computed(() => ({
    id: props.revision.id,
    title: `Revision Preview`,
    content: props.revision.content || "",
    model_class: "Page",
    update_time: props.revision.update_time,
}));

const revisionContent = computed(() => props.revision.content || "");
const changes = computed(() => computeLineDiff(revisionContent.value, props.currentContent));
const stats = computed(() => diffStats(changes.value));
const hasNoChanges = computed(() => revisionContent.value === props.currentContent);
</script>

<template>
    <div class="page-revision-view d-flex flex-column h-100" data-description="page revision view">
        <div class="revision-view-toolbar d-flex align-items-center p-2 border-bottom">
            <BButton variant="link" size="sm" data-description="revision back button" @click="emit('back')">
                <FontAwesomeIcon :icon="faArrowLeft" />
                Back to revisions
            </BButton>
            <span class="d-flex mx-2" data-description="revision view mode toggle">
                <BButton
                    :variant="viewMode === 'preview' ? 'primary' : 'outline-primary'"
                    size="sm"
                    data-description="revision preview button"
                    @click="emit('update:viewMode', 'preview')">
                    <FontAwesomeIcon :icon="faEye" />
                    Preview
                </BButton>
                <BButton
                    :variant="viewMode === 'changes' ? 'primary' : 'outline-primary'"
                    size="sm"
                    class="ml-1"
                    data-description="revision changes button"
                    @click="emit('update:viewMode', 'changes')">
                    <FontAwesomeIcon :icon="faExchangeAlt" />
                    Changes
                </BButton>
            </span>
            <span class="flex-grow-1"></span>
            <BButton
                variant="primary"
                size="sm"
                data-description="revision restore button"
                :disabled="isReverting"
                @click="emit('restore', revision.id)">
                <FontAwesomeIcon :icon="isReverting ? faSpinner : faUndo" :spin="isReverting" />
                Restore this version
            </BButton>
        </div>
        <div class="revision-view-content overflow-auto flex-grow-1">
            <Markdown
                v-if="viewMode === 'preview'"
                :markdown-config="markdownConfig"
                :read-only="true"
                download-endpoint="" />
            <div v-else class="revision-diff-view" data-description="revision diff view">
                <div v-if="hasNoChanges" class="p-3 text-muted text-center" data-description="revision no changes">
                    No changes — this revision matches the current content.
                </div>
                <template v-else>
                    <div class="diff-header d-flex align-items-center p-2">
                        <span class="diff-stats">
                            <span class="text-success">+{{ stats.additions }}</span>
                            <span class="mx-1">/</span>
                            <span class="text-danger">-{{ stats.deletions }}</span>
                            lines
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
                </template>
            </div>
        </div>
    </div>
</template>

<style scoped>
.revision-view-toolbar {
    background: var(--panel-header-bg);
}

.revision-diff-view {
    font-size: 0.85rem;
}

.diff-header {
    background: var(--panel-header-bg, #f8f9fa);
    border-bottom: 1px solid var(--border-color, #dee2e6);
}

.diff-content {
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
