<script setup lang="ts">
import { faBug, faGear, faShieldHalved } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GDropdownItemButton } from "@galaxyproject/galaxy-ui"
import { computed } from "vue"
import ActionMenu from "@/components/ActionMenu.vue"
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
    <ActionMenu :icon="faGear" label="Revision settings" dropup>
        <GDropdownItemButton v-if="!malicious" @click="setMalicious">
            <FontAwesomeIcon :icon="faBug" fixed-width />
            Mark as malicious
        </GDropdownItemButton>
        <GDropdownItemButton v-else @click="unsetMalicious">
            <FontAwesomeIcon :icon="faShieldHalved" fixed-width />
            Un-mark as malicious
        </GDropdownItemButton>
    </ActionMenu>
</template>
