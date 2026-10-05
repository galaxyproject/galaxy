<script setup lang="ts">
import type { RepositoryTool } from "@/schema"

interface RepositoryToolProps {
    tool: RepositoryTool
    changesetRevision: string
    trsToolId?: string
}

defineProps<RepositoryToolProps>()
</script>

<template>
    <li class="repository-tool">
        <div class="repository-tool-name">
            <router-link
                v-if="trsToolId"
                class="repository-tool-link"
                :to="`/tools/${trsToolId}/versions/${tool.version}?from_changeset_revision=${changesetRevision}`"
            >
                {{ tool.name }}
            </router-link>
            <span v-else>
                {{ tool.name }}
            </span>
            <span class="repository-tool-id">
                (<code>{{ tool.id }} / {{ tool.version }}</code
                >)
            </span>
        </div>
        <div class="repository-tool-description">
            {{ tool.description }}
        </div>
    </li>
</template>

<style scoped>
.repository-tool {
    padding: var(--spacing-2);
}

.repository-tool-name {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.repository-tool-link {
    color: var(--color-galaxy-primary);
    font-weight: 700;
}

.repository-tool-link:hover,
.repository-tool-link:focus-visible {
    text-decoration: underline;
}

.repository-tool-link:focus-visible {
    outline: 2px solid var(--color-galaxy-primary);
    outline-offset: 2px;
}

.repository-tool-id {
    margin-left: var(--spacing-1);
    color: var(--color-galaxy-primary);
    font-weight: 700;
    font-size: var(--font-size-small);
    text-transform: uppercase;
}

.repository-tool-description {
    overflow: hidden;
    margin-top: var(--spacing-1);
    color: var(--color-grey-600);
    font-size: var(--font-size-small);
    white-space: nowrap;
    text-overflow: ellipsis;
}
</style>
