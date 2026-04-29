<script setup lang="ts">
/**
 * Mode 2: Section-level patch view.
 * Shows per-section diffs with checkboxes. User picks which sections to apply.
 */
import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { applySectionPatches, diffStats, type SectionChange, sectionDiff } from "./sectionDiffUtils";

const props = defineProps<{
    original: string;
    proposed: string;
    stale?: boolean;
}>();

const emit = defineEmits<{
    (e: "accept", patchedContent: string): void;
    (e: "reject"): void;
}>();

const sections = computed(() => sectionDiff(props.original, props.proposed));
const changedSections = computed(() => sections.value.filter((s) => s.hasChanges));

// Track accepted section headings
const accepted = ref(new Set<string>());

function toggleSection(heading: string) {
    const next = new Set(accepted.value);
    if (next.has(heading)) {
        next.delete(heading);
    } else {
        next.add(heading);
    }
    accepted.value = next;
}

function selectAll() {
    accepted.value = new Set(changedSections.value.map((s) => sectionHeading(s)));
}

function selectNone() {
    accepted.value = new Set();
}

const acceptedCount = computed(() => accepted.value.size);

function applySelected() {
    const result = applySectionPatches(props.original, props.proposed, accepted.value);
    emit("accept", result);
}

function sectionHeading(sc: SectionChange): string {
    return sc.newSection?.heading ?? sc.oldSection?.heading ?? "";
}

function sectionLabel(sc: SectionChange): string {
    const heading = sectionHeading(sc);
    if (!heading) {
        return "(preamble)";
    }
    if (sc.oldSection === null) {
        return `${heading} (new)`;
    }
    if (sc.newSection === null) {
        return `${heading} (removed)`;
    }
    return heading;
}
</script>

<template>
    <div class="section-patch-view" data-description="section patch view">
        <div class="patch-header d-flex align-items-center justify-content-between p-2">
            <span>
                {{ changedSections.length }} section{{ changedSections.length !== 1 ? "s" : "" }} changed
                <template v-if="acceptedCount > 0"> &middot; {{ acceptedCount }} selected</template>
            </span>
            <span
                class="patch-actions"
                :title="stale ? 'Document has changed and this suggestion no longer applies.' : undefined">
                <BButton variant="link" size="sm" :disabled="stale" @click="selectAll">All</BButton>
                <BButton variant="link" size="sm" :disabled="stale" @click="selectNone">None</BButton>
                <BButton
                    variant="success"
                    size="sm"
                    :disabled="stale || acceptedCount === 0"
                    data-description="apply selected patches"
                    @click="applySelected">
                    <FontAwesomeIcon :icon="faCheck" />
                    Apply ({{ acceptedCount }})
                </BButton>
                <BButton
                    variant="outline-danger"
                    size="sm"
                    class="ml-1"
                    :disabled="stale"
                    data-description="reject all patches"
                    @click="emit('reject')">
                    <FontAwesomeIcon :icon="faTimes" />
                    Reject
                </BButton>
            </span>
        </div>
        <div class="patch-sections">
            <div
                v-for="(sc, idx) in changedSections"
                :key="idx"
                class="patch-section"
                :class="{ 'section-accepted': accepted.has(sectionHeading(sc)) }">
                <div class="section-header d-flex align-items-center p-2">
                    <BFormCheckbox
                        :checked="accepted.has(sectionHeading(sc))"
                        :data-description="`toggle section ${sectionHeading(sc)}`"
                        @change="toggleSection(sectionHeading(sc))">
                        <strong>{{ sectionLabel(sc) }}</strong>
                    </BFormCheckbox>
                    <span class="ml-auto diff-stats-inline">
                        <span class="text-success">+{{ diffStats(sc.changes).additions }}</span>
                        <span class="text-danger ml-1">-{{ diffStats(sc.changes).deletions }}</span>
                    </span>
                </div>
                <div class="section-diff">
                    <div v-for="(change, ci) in sc.changes" :key="ci">
                        <pre
                            v-for="(line, li) in change.value.split('\n').slice(0, -1)"
                            :key="`${ci}-${li}`"
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
        </div>
    </div>
</template>

<style scoped>
.section-patch-view {
    border: 1px solid var(--border-color, #dee2e6);
    border-radius: 4px;
    margin: 0.5rem 0;
    font-size: 0.85rem;
}

.patch-header {
    background: var(--panel-header-bg, #f8f9fa);
    border-bottom: 1px solid var(--border-color, #dee2e6);
}

.patch-section {
    border-bottom: 1px solid var(--border-color, #dee2e6);
}

.patch-section:last-child {
    border-bottom: none;
}

.section-accepted {
    background-color: rgba(40, 167, 69, 0.04);
}

.section-header {
    background: var(--panel-header-bg, #f8f9fa);
}

.section-diff {
    max-height: 200px;
    overflow: auto;
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

.diff-stats-inline {
    font-size: 0.75rem;
}
</style>
