<script setup lang="ts">
import { ref, computed, watch } from "vue"
import MetadataJsonViewer from "./MetadataJsonViewer.vue"
import type { components } from "@/schema"

type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]

interface Props {
    metadata: RepositoryMetadata | null
}
const props = defineProps<Props>()

const revisionKeys = computed(() => {
    if (!props.metadata) return []
    return Object.keys(props.metadata).sort((a, b) => {
        const [numA] = a.split(":")
        const [numB] = b.split(":")
        return parseInt(numB) - parseInt(numA) // Newest first
    })
})

const selectedRevision = ref<string>("")

watch(
    revisionKeys,
    (keys) => {
        if (keys.length > 0 && !selectedRevision.value) {
            selectedRevision.value = keys[0] // Default to newest
        }
    },
    { immediate: true }
)

const currentRevisionData = computed(() => {
    if (!props.metadata || !selectedRevision.value) return null
    return props.metadata[selectedRevision.value]
})
</script>

<template>
    <div>
        <div class="q-mb-md">
            <q-select
                v-model="selectedRevision"
                :options="revisionKeys"
                label="Revision"
                dense
                outlined
                style="max-width: 300px"
            />
        </div>

        <MetadataJsonViewer
            v-if="currentRevisionData"
            :data="currentRevisionData"
            model-name="RepositoryRevisionMetadata"
        />
        <div v-else class="text-grey">No metadata available</div>
    </div>
</template>
