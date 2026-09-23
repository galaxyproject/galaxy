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
    <span class="repository-select row items-center">
        <span class="repository-select-label text-h5 q-mr-lg">Revision</span>
        <!-- icon format_list_numbered -->
        <q-select
            filled
            dense
            v-model="selection"
            use-input
            :options="options"
            map-options
            emit-value
            class="q-mr-sm"
            style="width: 350px"
        >
            <template #no-option>
                <q-item>
                    <q-item-section class="text-grey"> No revisions </q-item-section>
                </q-item>
            </template>
        </q-select>
        <q-badge v-if="isLatest" color="positive"> newest revision </q-badge>
        <q-badge color="warning" v-else> newer revision(s) available </q-badge>
        <slot></slot>
    </span>
</template>
