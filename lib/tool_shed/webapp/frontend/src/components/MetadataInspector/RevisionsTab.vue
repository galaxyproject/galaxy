<script setup lang="ts">
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function depSummary(data: any): string {
    const repoDeps = data.repository_dependencies?.length || 0
    const toolDeps = data.tool_dependencies ? Object.keys(data.tool_dependencies).length : 0
    const parts = []
    if (repoDeps > 0) parts.push(`${repoDeps} repo dep${repoDeps > 1 ? "s" : ""}`)
    if (toolDeps > 0) parts.push(`${toolDeps} tool dep${toolDeps > 1 ? "s" : ""}`)
    return parts.length > 0 ? parts.join(", ") : "No dependencies"
}

// Auto-expand if prop provided
watch(
    () => props.expandRevision,
    (revision) => {
        if (revision) {
            expandedRevisions.value.add(revision)
        }
    },
    { immediate: true }
)
</script>

<template>
    <div>
        <div v-if="sortedRevisions.length === 0" class="text-grey">No revisions found.</div>

        <q-list bordered separator v-else>
            <q-expansion-item
                v-for="rev in sortedRevisions"
                :key="rev.key"
                :model-value="expandedRevisions.has(rev.key)"
                @update:model-value="toggleExpand(rev.key)"
                expand-icon-toggle
            >
                <template v-slot:header>
                    <q-item-section avatar>
                        <q-icon
                            :name="rev.data.downloadable ? 'sym_r_check_circle' : 'sym_r_cancel'"
                            :color="rev.data.downloadable ? 'positive' : 'negative'"
                        />
                    </q-item-section>
                    <q-item-section>
                        <q-item-label>[{{ rev.numericRevision }}:{{ rev.hash.substring(0, 7) }}]</q-item-label>
                        <q-item-label caption>{{ toolSummary(rev.data) }}</q-item-label>
                        <q-item-label caption>{{ depSummary(rev.data) }}</q-item-label>
                    </q-item-section>
                    <q-item-section side v-if="rev.data.invalid_tools?.length > 0">
                        <q-badge color="warning" :label="`${rev.data.invalid_tools.length} invalid`" />
                    </q-item-section>
                </template>

                <q-card>
                    <q-card-section v-if="rev.data.invalid_tools?.length > 0">
                        <div class="text-subtitle2 text-negative">Invalid Tools:</div>
                        <ul class="q-my-none">
                            <li v-for="path in rev.data.invalid_tools" :key="path">
                                <code>{{ path }}</code>
                            </li>
                        </ul>
                    </q-card-section>
                    <q-card-section>
                        <MetadataJsonViewer :data="rev.data" modelName="RepositoryRevisionMetadata" />
                    </q-card-section>
                </q-card>
            </q-expansion-item>
        </q-list>
    </div>
</template>
