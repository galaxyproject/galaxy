<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faChevronDown, faChevronRight, faCircleCheck, faCircleXmark } from "@fortawesome/free-solid-svg-icons"
import { GButton, GCollapse } from "@galaxyproject/galaxy-ui"
import { ref, computed, watch } from "vue"
import MetadataJsonViewer from "./MetadataJsonViewer.vue"
import type { components } from "@/schema"

type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]

interface Props {
    metadata: RepositoryMetadata | null
    expandRevision?: string | null // Auto-expand this revision
}
const props = withDefaults(defineProps<Props>(), {
    expandRevision: null,
})

const expandedRevisions = ref<Set<string>>(new Set())

const sortedRevisions = computed(() => {
    if (!props.metadata) return []
    return Object.entries(props.metadata)
        .map(([key, data]) => {
            const [numStr, hash] = key.split(":")
            return { key, numericRevision: parseInt(numStr), hash, data }
        })
        .sort((a, b) => b.numericRevision - a.numericRevision) // Newest first
})

function toggleExpand(key: string) {
    if (expandedRevisions.value.has(key)) {
        expandedRevisions.value.delete(key)
    } else {
        expandedRevisions.value.add(key)
    }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toolSummary(data: any): string {
    const tools = data.tools || []
    if (tools.length === 0) return "No tools"
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return tools.map((t: any) => `${t.id} (${t.version})`).join(", ")
}

// Auto-expand if prop provided
watch(
    () => props.expandRevision,
    (revision) => {
        if (revision) {
            expandedRevisions.value.add(revision)
        }
    },
    { immediate: true },
)
</script>

<template>
    <div>
        <div v-if="sortedRevisions.length === 0" class="revisions-empty">No revisions found.</div>

        <ul v-else class="revision-list">
            <li v-for="rev in sortedRevisions" :key="rev.key" class="revision-entry">
                <div class="revision-item">
                    <FontAwesomeIcon
                        class="revision-status"
                        :icon="rev.data.downloadable ? faCircleCheck : faCircleXmark"
                        :class="rev.data.downloadable ? 'revision-status--downloadable' : 'revision-status--blocked'"
                    />
                    <div class="revision-summary">
                        <div>[{{ rev.numericRevision }}:{{ rev.hash.substring(0, 7) }}]</div>
                        <div class="revision-caption">{{ toolSummary(rev.data) }}</div>
                    </div>
                    <span v-if="rev.data.invalid_tools?.length > 0" class="invalid-tools-badge"
                        >{{ rev.data.invalid_tools.length }} invalid</span
                    >
                    <GButton
                        class="revision-toggle"
                        transparent
                        :aria-expanded="expandedRevisions.has(rev.key)"
                        :aria-controls="`revision-${rev.numericRevision}-details`"
                        :aria-label="`Details for revision ${rev.numericRevision}`"
                        @click="toggleExpand(rev.key)"
                    >
                        <FontAwesomeIcon :icon="expandedRevisions.has(rev.key) ? faChevronDown : faChevronRight" />
                    </GButton>
                </div>

                <GCollapse :id="`revision-${rev.numericRevision}-details`" :value="expandedRevisions.has(rev.key)">
                    <template #default="{ contentActive }">
                        <div v-if="contentActive" class="revision-details">
                            <div v-if="rev.data.invalid_tools?.length > 0" class="revision-details-section">
                                <div class="invalid-tools-heading">Invalid Tools:</div>
                                <ul class="invalid-tools-list">
                                    <li v-for="tool in rev.data.invalid_tools" :key="tool.tool_config">
                                        <code>{{ tool.tool_config }}</code
                                        >: {{ tool.error_message }}
                                    </li>
                                </ul>
                            </div>
                            <div class="revision-details-section">
                                <MetadataJsonViewer :data="rev.data" model-name="RepositoryRevisionMetadata" />
                            </div>
                        </div>
                    </template>
                </GCollapse>
            </li>
        </ul>
    </div>
</template>

<style scoped>
.revisions-empty {
    color: var(--color-grey-500);
}

.revision-list {
    margin: 0;
    padding: 0;
    list-style: none;
    border: 1px solid var(--color-grey-200);
}

.revision-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-4);
    min-height: 3rem;
    padding: var(--spacing-2) var(--spacing-4);
}

.revision-status {
    flex: none;
    width: 1.5rem;
}

.revision-status--downloadable {
    color: var(--color-green-500);
}

.revision-status--blocked {
    color: var(--color-red-600);
}

.revision-summary {
    flex: 1 1 auto;
    min-width: 0;
}

.revision-caption {
    color: var(--color-grey-600);
    font-size: var(--font-size-small);
}

.revision-entry + .revision-entry {
    border-top: 1px solid var(--color-grey-200);
}

.revision-details {
    background: var(--background-color);
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.revision-details-section {
    padding: var(--spacing-4);
}

.invalid-tools-heading {
    color: var(--color-red-600);
    font-size: 0.875rem;
    font-weight: 500;
}

.invalid-tools-list {
    margin-top: 0;
    margin-bottom: 0;
}

.invalid-tools-badge {
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--spacing-1);
    background: var(--color-yellow-600);
    color: var(--color-yellow-900);
    font-size: var(--font-size-small);
    font-weight: 600;
    line-height: 1;
    white-space: nowrap;
}
</style>
