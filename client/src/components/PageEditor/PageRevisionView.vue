<script setup lang="ts">
import { faArrowLeft, faExchangeAlt, faEye, faSpinner, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { PageRevisionDetails } from "@/api/pages";

import { computeLineDiff, diffStats } from "./sectionDiffUtils";

import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

type ViewMode = "preview" | "changes_current" | "changes_previous";

const props = defineProps<{
    revision: PageRevisionDetails;
    currentContent: string;
    previousContent: string | null;
    isNewestRevision: boolean;
    isOldestRevision: boolean;
    viewMode: ViewMode;
    isReverting: boolean;
}>();

const emit = defineEmits<{
    (e: "back"): void;
    (e: "restore", revisionId: string): void;
    (e: "update:viewMode", mode: ViewMode): void;
}>();

const markdownConfig = computed(() => ({
    id: props.revision.id,
    title: `Revision Preview`,
    content: props.revision.content || "",
    model_class: "Page",
    update_time: props.revision.update_time,
}));

const revisionContent = computed(() => props.revision.content || "");
const currentChanges = computed(() => computeLineDiff(revisionContent.value, props.currentContent));
const currentStats = computed(() => diffStats(currentChanges.value));
const hasNoCurrentChanges = computed(() => revisionContent.value === props.currentContent);

const previousChanges = computed(() => computeLineDiff(props.previousContent ?? "", revisionContent.value));
const previousStats = computed(() => diffStats(previousChanges.value));
const hasNoPreviousChanges = computed(() => (props.previousContent ?? "") === revisionContent.value);

const activeChanges = computed(() =>
    props.viewMode === "changes_current" ? currentChanges.value : previousChanges.value,
);
const activeStats = computed(() => (props.viewMode === "changes_current" ? currentStats.value : previousStats.value));
const activeHasNoChanges = computed(() =>
    props.viewMode === "changes_current" ? hasNoCurrentChanges.value : hasNoPreviousChanges.value,
);
</script>

<template>
    <div class="page-revision-view d-flex flex-column h-100" data-description="page revision view">
        <div class="revision-view-toolbar border-bottom">
            <div class="d-flex">
                <GButtonGroup data-description="revision view mode toggle">
                    <GButton
                        color="blue"
                        outline
                        :pressed="viewMode === 'preview'"
                        data-description="revision preview button"
                        size="small"
                        @click="emit('update:viewMode', 'preview')">
                        <FontAwesomeIcon :icon="faEye" />
                        Preview
                    </GButton>
                    <GButton
                        v-if="!isNewestRevision"
                        color="blue"
                        outline
                        :pressed="viewMode === 'changes_current'"
                        data-description="revision compare current button"
                        size="small"
                        @click="emit('update:viewMode', 'changes_current')">
                        <FontAwesomeIcon :icon="faExchangeAlt" />
                        Compare to Current
                    </GButton>
                    <GButton
                        v-if="!isOldestRevision"
                        color="blue"
                        outline
                        :pressed="viewMode === 'changes_previous'"
                        data-description="revision compare previous button"
                        size="small"
                        @click="emit('update:viewMode', 'changes_previous')">
                        <FontAwesomeIcon :icon="faExchangeAlt" />
                        Compare to Previous
                    </GButton>
                </GButtonGroup>

                <div v-if="!activeHasNoChanges" class="d-flex align-items-center px-2">
                    <span class="diff-stats">
                        <span class="text-success">+{{ activeStats.additions }}</span>
                        <span class="mx-1">/</span>
                        <span class="text-danger">-{{ activeStats.deletions }}</span>
                        lines
                    </span>
                </div>
            </div>

            <div class="d-flex flex-gapx-1 align-items-center">
                <GButton
                    color="blue"
                    transparent
                    size="small"
                    data-description="revision back button"
                    @click="emit('back')">
                    <FontAwesomeIcon :icon="faArrowLeft" />
                    Exit Revision
                </GButton>
                <GButton
                    color="blue"
                    size="small"
                    title="Restore this version"
                    tooltip
                    data-description="revision restore button"
                    :disabled="isReverting"
                    @click="emit('restore', revision.id)">
                    <FontAwesomeIcon :icon="isReverting ? faSpinner : faUndo" :spin="isReverting" />
                    Restore
                </GButton>
            </div>
        </div>

        <div class="revision-view-content overflow-auto flex-grow-1">
            <Markdown
                v-if="viewMode === 'preview'"
                class="px-3 pt-3"
                :markdown-config="markdownConfig"
                no-heading
                :read-only="true"
                download-endpoint="" />
            <div
                v-else-if="viewMode === 'changes_current' || viewMode === 'changes_previous'"
                class="revision-diff-view"
                data-description="revision diff view">
                <div
                    v-if="activeHasNoChanges"
                    class="p-3 text-muted text-center"
                    data-description="revision no changes">
                    No changes — this revision matches the
                    {{ viewMode === "changes_current" ? "current content" : "previous revision" }}.
                </div>
                <template v-else>
                    <div class="diff-content">
                        <div v-for="(change, idx) in activeChanges" :key="idx" class="diff-block">
                            <pre
                                v-for="(line, li) in change.value.replace(/\n$/, '').split('\n')"
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
    background: var(--color-grey-100);
    display: flex;
    align-items: center;
    padding: 0.5rem 1rem;
    gap: 0.5rem;
    justify-content: space-between;
}

.revision-diff-view {
    font-size: 0.85rem;
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
