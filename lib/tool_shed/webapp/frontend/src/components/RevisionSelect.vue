<script setup lang="ts">
import { computed } from "vue"
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
        opts.push({
            label: key,
            value: revisions[key]?.changeset_revision,
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
            style="width: 250px"
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
