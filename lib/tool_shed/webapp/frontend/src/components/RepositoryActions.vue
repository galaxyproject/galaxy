<script setup lang="ts">
import { ToolShedApi } from "@/schema"
import { notify, notifyOnCatch } from "@/util"

async function resetMetadata() {
    ToolShedApi()
        .POST("/api/repositories/{encoded_repository_id}/reset_metadata", {
            params: { path: { encoded_repository_id: props.repositoryId } },
        })
        .catch(notifyOnCatch)
        .then(() => {
            notify("Repository metadata reset.")
            emits("update")
        })
}

const props = defineProps({
    repositoryId: {
        type: String,
        required: true,
    },
    deprecated: {
        type: Boolean,
        required: true,
    },
})
type Emits = {
    (eventName: "update"): void
    (eventName: "deprecate"): void
    (eventName: "undeprecate"): void
}

const emits = defineEmits<Emits>()
</script>
<template>
    <q-fab class="q-px-sm" color="secondary" text-color="primary" icon="settings" direction="down">
        <q-fab-action color="primary" icon="history" @click="resetMetadata" label="Reset Metadata" />
        <q-fab-action
            color="primary"
            icon="warning"
            @click="$emit('undeprecate')"
            label="Un-mark as Deprecated"
            v-if="deprecated"
        />
        <q-fab-action color="primary" icon="warning" @click="$emit('deprecate')" label="Mark as Deprecated" v-else />
    </q-fab>
</template>
