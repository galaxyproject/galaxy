<script setup lang="ts">
import { GButton, GCollapse } from "@galaxyproject/galaxy-ui"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faArrowRight, faChevronDown, faChevronRight } from "@fortawesome/free-solid-svg-icons"
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
    name: string
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
                name: tool.name,
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

function detailsKey(toolId: string, revision: string): string {
    return `${toolId}-${revision}`
}

function isExpanded(toolId: string, revision: string): boolean {
    return expandedTools.value.has(detailsKey(toolId, revision))
}

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

        <q-card v-for="(history, historyIndex) in toolHistories" :key="history.toolId" class="q-mb-md">
            <q-card-section>
                <div class="text-h6">{{ history.toolId }}</div>
            </q-card-section>

            <ol class="tool-history-timeline">
                <li v-for="(ver, versionIndex) in history.versions" :key="ver.revision" class="tool-history-entry">
                    <div class="tool-history-subtitle">{{ ver.name }} {{ ver.description }}</div>
                    <div class="tool-history-title">
                        <div class="row items-center q-gutter-sm">
                            <span class="text-weight-medium">{{ ver.version }}</span>
                            <span class="revision-badge">[{{ ver.numericRevision }}]</span>
                            <GButton size="small" transparent @click="emit('goToRevision', ver.revision)">
                                <FontAwesomeIcon :icon="faArrowRight" class="q-mr-xs" />
                                Rev {{ ver.numericRevision }}
                            </GButton>
                        </div>
                    </div>

                    <GButton
                        class="tool-details-toggle"
                        size="small"
                        transparent
                        :aria-expanded="isExpanded(history.toolId, ver.revision)"
                        :aria-controls="`tool-details-${historyIndex}-${versionIndex}`"
                        @click="toggleTool(detailsKey(history.toolId, ver.revision))"
                    >
                        <FontAwesomeIcon
                            :icon="isExpanded(history.toolId, ver.revision) ? faChevronDown : faChevronRight"
                        />
                        Tool Details
                    </GButton>
                    <GCollapse
                        :id="`tool-details-${historyIndex}-${versionIndex}`"
                        :value="isExpanded(history.toolId, ver.revision)"
                    >
                        <template #default="{ contentActive }">
                            <MetadataJsonViewer
                                v-if="contentActive"
                                :data="ver.tool"
                                model-name="RepositoryTool"
                                :deep="3"
                            />
                        </template>
                    </GCollapse>
                </li>
            </ol>
        </q-card>
    </div>
</template>

<style scoped>
.tool-history-timeline {
    margin: 0;
    padding: 0 var(--spacing-4) var(--spacing-2);
    list-style: none;
}

.tool-history-entry {
    position: relative;
    padding: 0 0 var(--spacing-4) var(--spacing-8);
}

.tool-history-entry::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: calc(var(--spacing-3) - 1px);
    width: 2px;
    background: var(--color-grey-200);
}

.tool-history-entry:last-child::before {
    bottom: auto;
    height: var(--spacing-3);
}

.tool-history-entry::after {
    content: "";
    position: absolute;
    top: var(--spacing-1);
    left: calc(var(--spacing-3) - var(--spacing-2));
    width: var(--spacing-4);
    height: var(--spacing-4);
    box-sizing: border-box;
    border: 3px solid var(--color-galaxy-primary);
    border-radius: 50%;
    background: var(--background-color);
}

.tool-history-subtitle {
    color: var(--color-grey-500);
    font-size: var(--font-size-small);
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

.tool-history-title {
    margin-bottom: var(--spacing-1);
}

.revision-badge {
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--spacing-1);
    background: var(--color-grey-500);
    color: var(--color-grey-100);
    font-size: var(--font-size-small);
    line-height: 1;
    white-space: nowrap;
}
</style>
