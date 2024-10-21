<script setup lang="ts">
import { computed } from "vue"
import { RevisionMetadata } from "@/schema"
import { ToolShedApi } from "@/schema"
import { notify, notifyOnCatch } from "@/util"

interface RevisionActionsProps {
    repositoryId: string
    currentMetadata: RevisionMetadata
}

const props = defineProps<RevisionActionsProps>()

async function setMalicious() {
    ToolShedApi()
        .PUT("/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/malicious", {
            params: {
                path: {
                    encoded_repository_id: props.repositoryId,
                    changeset_revision: props.currentMetadata.changeset_revision,
                },
            },
        })
        .catch(notifyOnCatch)
        .then(() => {
            notify("Marked repository as malicious")
            emits("update")
        })
}

async function unsetMalicious() {
    ToolShedApi()
        .DELETE("/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/malicious", {
            params: {
                path: {
                    encoded_repository_id: props.repositoryId,
                    changeset_revision: props.currentMetadata.changeset_revision,
                },
            },
        })
        .catch(notifyOnCatch)
        .then(() => {
            notify("Un-marked repository as malicious")
            emits("update")
        })
}

const malicious = computed(() => props.currentMetadata.malicious)
type Emits = {
    (eventName: "update"): void
}

const emits = defineEmits<Emits>()
</script>
<template>
    <q-fab padding="sm" class="q-px-md" color="secondary" text-color="primary" icon="settings" direction="up">
        <q-fab-action
            color="primary"
            icon="history"
            @click="setMalicious"
            label="Mark as malicious"
            v-if="!malicious"
        />
        <q-fab-action color="primary" icon="history" @click="unsetMalicious" label="Un-mark as malicious" v-else />
    </q-fab>
</template>
