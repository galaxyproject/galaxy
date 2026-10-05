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
        <div v-if="sortedRevisions.length === 0" class="text-grey">No revisions found.</div>

        <q-list bordered separator v-else>
            <div v-for="rev in sortedRevisions" :key="rev.key" class="revision-entry">
                <q-item>
                    <q-item-section avatar>
                        <FontAwesomeIcon
                            :icon="rev.data.downloadable ? faCircleCheck : faCircleXmark"
                            :class="rev.data.downloadable ? 'text-positive' : 'text-negative'"
                        />
                    </q-item-section>
                    <q-item-section>
                        <q-item-label>[{{ rev.numericRevision }}:{{ rev.hash.substring(0, 7) }}]</q-item-label>
                        <q-item-label caption>{{ toolSummary(rev.data) }}</q-item-label>
                    </q-item-section>
                    <q-item-section side v-if="rev.data.invalid_tools?.length > 0">
                        <q-badge color="warning" :label="`${rev.data.invalid_tools.length} invalid`" />
                    </q-item-section>
                    <q-item-section side>
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
                    </q-item-section>
                </q-item>

                <GCollapse :id="`revision-${rev.numericRevision}-details`" :value="expandedRevisions.has(rev.key)">
                    <template #default="{ contentActive }">
                        <q-card v-if="contentActive">
                            <q-card-section v-if="rev.data.invalid_tools?.length > 0">
                                <div class="text-subtitle2 text-negative">Invalid Tools:</div>
                                <ul class="q-my-none">
                                    <li v-for="tool in rev.data.invalid_tools" :key="tool.tool_config">
                                        <code>{{ tool.tool_config }}</code
                                        >: {{ tool.error_message }}
                                    </li>
                                </ul>
                            </q-card-section>
                            <q-card-section>
                                <MetadataJsonViewer :data="rev.data" model-name="RepositoryRevisionMetadata" />
                            </q-card-section>
                        </q-card>
                    </template>
                </GCollapse>
            </div>
        </q-list>
    </div>
</template>

<style scoped>
.revision-entry + .revision-entry {
    border-top: 1px solid var(--color-grey-200);
}
</style>
