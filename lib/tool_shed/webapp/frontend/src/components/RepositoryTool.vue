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
            <span v-else class="repository-tool-title">
                {{ tool.name }}
            </span>
            <span class="repository-tool-version">v{{ tool.version }}</span>
        </div>
        <div v-if="tool.description" class="repository-tool-description">
            {{ tool.description }}
        </div>
        <code class="repository-tool-id">{{ tool.id }}</code>
    </li>
</template>

<style scoped>
.repository-tool {
    padding: 0.85rem 1.25rem;
}

.repository-tool + .repository-tool {
    border-top: 1px solid var(--shed-border-subtle);
}

.repository-tool-name {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.6rem;
}

.repository-tool-link,
.repository-tool-title {
    font-size: 1.05rem;
    font-weight: 700;
}

.repository-tool-link:focus-visible {
    outline: 2px solid var(--color-galaxy-primary);
    outline-offset: 2px;
}

.repository-tool-version {
    padding: 0 0.5rem;
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1.6;
    color: var(--color-bay-of-many-900, #25537b);
    background: var(--color-bay-of-many-100, #edf4fa);
    border: 1px solid var(--color-bay-of-many-200, #cde0f0);
    border-radius: 999px;
}

.repository-tool-description {
    margin-top: 0.2rem;
    color: var(--shed-text);
}

.repository-tool .repository-tool-id {
    display: inline-block;
    margin-top: 0.35rem;
    padding: 0;
    font-size: 0.78rem;
    color: var(--shed-muted);
    background: none;
    overflow-wrap: anywhere;
}
</style>
