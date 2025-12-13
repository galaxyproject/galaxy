<script setup lang="ts">
import { computed, ref } from "vue"
import MetadataJsonViewer from "./MetadataJsonViewer.vue"
import type { components } from "@/schema"

type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]
type RepositoryTool = components["schemas"]["RepositoryTool"]

interface Props {
    metadata: RepositoryMetadata | null
}
const props = defineProps<Props>()
const emit = defineEmits<{
    (e: "goToRevision", revision: string): void
}>()

interface ToolVersion {
    revision: string
    numericRevision: number
    version: string
    description: string
    tool: RepositoryTool
}

interface ToolHistory {
    toolId: string
    versions: ToolVersion[]
}

const expandedTools = ref<Set<string>>(new Set())

const toolHistories = computed<ToolHistory[]>(() => {
    if (!props.metadata) return []

    const byToolId = new Map<string, ToolVersion[]>()

    for (const [key, revData] of Object.entries(props.metadata)) {
        const [numStr] = key.split(":")
        const numericRevision = parseInt(numStr)

        for (const tool of revData.tools || []) {
            if (!byToolId.has(tool.id)) {
                byToolId.set(tool.id, [])
            }
            byToolId.get(tool.id)!.push({
                revision: key,
                numericRevision,
                version: tool.version,
                description: tool.description,
                tool,
            })
        }
    }

    // Sort each tool's versions by revision (newest first)
    const result: ToolHistory[] = []
    for (const [toolId, versions] of byToolId) {
        versions.sort((a, b) => b.numericRevision - a.numericRevision)
        result.push({ toolId, versions })
    }

    // Sort tools alphabetically
    result.sort((a, b) => a.toolId.localeCompare(b.toolId))
    return result
})

function toggleTool(toolId: string) {
    if (expandedTools.value.has(toolId)) {
        expandedTools.value.delete(toolId)
    } else {
        expandedTools.value.add(toolId)
    }
}
</script>

<template>
    <div>
        <div v-if="toolHistories.length === 0" class="text-grey">No tools found in this repository.</div>

        <q-card v-for="history in toolHistories" :key="history.toolId" class="q-mb-md">
            <q-card-section>
                <div class="text-h6">{{ history.toolId }}</div>
            </q-card-section>

            <q-timeline color="primary" layout="dense" class="q-px-md">
                <q-timeline-entry v-for="ver in history.versions" :key="ver.revision" :subtitle="ver.description">
                    <template v-slot:title>
                        <div class="row items-center q-gutter-sm">
                            <span class="text-weight-medium">{{ ver.version }}</span>
                            <q-badge color="grey-6">[{{ ver.numericRevision }}]</q-badge>
                            <q-btn
                                flat
                                dense
                                size="sm"
                                icon="sym_r_arrow_forward"
                                :label="`Rev ${ver.numericRevision}`"
                                @click="emit('goToRevision', ver.revision)"
                            />
                        </div>
                    </template>

                    <q-expansion-item
                        dense
                        label="Tool Details"
                        :model-value="expandedTools.has(`${history.toolId}-${ver.revision}`)"
                        @update:model-value="toggleTool(`${history.toolId}-${ver.revision}`)"
                    >
                        <MetadataJsonViewer :data="ver.tool" modelName="RepositoryTool" :deep="3" />
                    </q-expansion-item>
                </q-timeline-entry>
            </q-timeline>
        </q-card>
    </div>
</template>
