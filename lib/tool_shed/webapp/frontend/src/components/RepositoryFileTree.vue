<script setup lang="ts">
import { computed, ref, watch } from "vue"
import type { RepositoryFileEntry } from "@/api"
import { ancestorsOf, buildFileTree } from "@/components/fileTree"
import RepositoryFileTreeNodes from "@/components/RepositoryFileTreeNodes.vue"

interface Props {
    files: RepositoryFileEntry[]
    selected?: string | null
}

const props = withDefaults(defineProps<Props>(), {
    selected: null,
})

const emit = defineEmits<{
    (e: "select", path: string): void
}>()

const tree = computed(() => buildFileTree(props.files))
const expanded = ref<string[]>([])

function toggle(path: string) {
    expanded.value = expanded.value.includes(path)
        ? expanded.value.filter((p) => p !== path)
        : [...expanded.value, path]
}

watch(
    () => props.selected,
    (selected) => {
        if (selected) {
            const closed = ancestorsOf(selected).filter((path) => !expanded.value.includes(path))
            expanded.value = [...expanded.value, ...closed]
        }
    },
    { immediate: true },
)
</script>

<template>
    <RepositoryFileTreeNodes
        class="repository-file-tree"
        :nodes="tree"
        :expanded="expanded"
        :selected="selected"
        @toggle="toggle"
        @select="emit('select', $event)"
    />
</template>
