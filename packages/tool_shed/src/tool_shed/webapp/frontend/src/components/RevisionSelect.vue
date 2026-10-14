<script setup lang="ts">
import { computed } from "vue"
import { parseISO, format } from "date-fns"
import { useModelWrapper } from "@/modelWrapper"

import { components } from "@/schema"

type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]

interface RevisionSelectProps {
    revisions: RepositoryMetadata
    modelValue: string
}

const props = withDefaults(defineProps<RevisionSelectProps>(), {
    modelValue: "",
})

const options = computed(() => {
    const opts = []
    const revisions = props.revisions || {}
    for (const key of Object.keys(revisions)) {
        const revision = revisions[key]
        let label = key
        if (revision?.create_time) {
            const date = parseISO(`${revision.create_time}Z`)
            label = `${key} (${format(date, "yyyy-MM-dd")})`
        }
        opts.push({
            label,
            value: revision?.changeset_revision,
        })
    }
    return opts
})

const isLatest = computed(() => {
    const currentValue = props.modelValue
    const optionsArray = options.value
    const lastOption = optionsArray[optionsArray.length - 1]
    return lastOption && currentValue == lastOption.value
})

const emit = defineEmits<{ (event: string, newValue: string): void }>()
const selection = useModelWrapper(props, emit, "modelValue")
</script>

<template>
    <div class="repository-select">
        <span class="repository-select-label">Revision</span>
        <q-select
            outlined
            dense
            v-model="selection"
            use-input
            :options="options"
            map-options
            emit-value
            class="repository-select-input"
        >
            <template #no-option>
                <q-item>
                    <q-item-section class="text-grey"> No revisions </q-item-section>
                </q-item>
            </template>
        </q-select>
        <span v-if="isLatest" class="revision-status revision-status-latest">Newest revision</span>
        <span v-else class="revision-status revision-status-older">Newer revision(s) available</span>
        <slot></slot>
    </div>
</template>

<style scoped>
.repository-select {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
}

.repository-select-label {
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--shed-muted);
}

.repository-select-input {
    width: 22rem;
    max-width: 100%;
    background: #fff;
}

.revision-status {
    padding: 0.15rem 0.65rem;
    font-size: 0.78rem;
    font-weight: 700;
    border-radius: 999px;
    border: 1px solid;
}

.revision-status-latest {
    color: var(--color-green-700);
    background: var(--color-green-100);
    border-color: var(--color-green-300);
}

.revision-status-older {
    color: var(--color-orange-700);
    background: var(--color-orange-100);
    border-color: var(--color-orange-300);
}
</style>
