<script setup lang="ts">
import { faFile, faFolder, faFolderOpen, faLink } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import type { RepositoryFileEntry } from "@/api"
import type { FileTreeNode } from "@/components/fileTree"

interface Props {
    nodes: FileTreeNode<RepositoryFileEntry>[]
    expanded: string[]
    selected: string | null
}

defineProps<Props>()

const emit = defineEmits<{
    (e: "toggle", path: string): void
    (e: "select", path: string): void
}>()
</script>

<template>
    <ul class="file-tree-nodes">
        <li v-for="node in nodes" :key="node.path">
            <template v-if="node.kind === 'folder'">
                <button
                    type="button"
                    class="file-tree-item"
                    :aria-expanded="expanded.includes(node.path)"
                    @click="emit('toggle', node.path)"
                >
                    <FontAwesomeIcon
                        :icon="expanded.includes(node.path) ? faFolderOpen : faFolder"
                        class="file-tree-icon file-tree-folder-icon"
                        fixed-width
                    />
                    <span class="file-tree-name">{{ node.name }}</span>
                </button>
                <RepositoryFileTreeNodes
                    v-if="expanded.includes(node.path)"
                    class="file-tree-children"
                    :nodes="node.children"
                    :expanded="expanded"
                    :selected="selected"
                    @toggle="emit('toggle', $event)"
                    @select="emit('select', $event)"
                />
            </template>
            <button
                v-else
                type="button"
                class="file-tree-item"
                :aria-current="node.path === selected ? 'true' : undefined"
                @click="emit('select', node.path)"
            >
                <FontAwesomeIcon
                    :icon="node.entry.type === 'symlink' ? faLink : faFile"
                    class="file-tree-icon"
                    fixed-width
                />
                <span class="file-tree-name">{{ node.name }}</span>
            </button>
        </li>
    </ul>
</template>

<style scoped>
.file-tree-nodes {
    margin: 0;
    padding: 0;
    list-style: none;
}

.file-tree-children {
    margin-left: 0.85rem;
    padding-left: 0.4rem;
    border-left: 1px solid var(--shed-border-subtle);
}

.file-tree-item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    padding: 0.3rem 0.5rem;
    border: none;
    border-radius: var(--shed-radius-sm);
    background: none;
    color: var(--shed-text);
    font: inherit;
    font-size: 0.9rem;
    text-align: left;
    cursor: pointer;
    transition: background-color var(--shed-transition);
}

.file-tree-item:hover {
    background: color-mix(in srgb, var(--shed-page-bg) 70%, white);
}

.file-tree-item[aria-current="true"] {
    background: var(--shed-page-bg);
    color: var(--shed-heading);
    font-weight: 700;
    box-shadow: inset 3px 0 0 var(--shed-gold);
}

.file-tree-icon {
    flex: none;
    color: var(--shed-muted);
}

.file-tree-folder-icon {
    color: var(--shed-link);
}

.file-tree-name {
    min-width: 0;
    overflow-wrap: anywhere;
}
</style>
