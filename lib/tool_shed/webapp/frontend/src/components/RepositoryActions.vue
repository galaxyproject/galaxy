<script setup lang="ts">
import { faArrowsRotate, faGear, faTriangleExclamation } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GDropdownItemButton } from "@galaxyproject/galaxy-ui"
import ActionMenu from "@/components/ActionMenu.vue"
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
    <ActionMenu :icon="faGear" label="Repository settings">
        <GDropdownItemButton @click="resetMetadata">
            <FontAwesomeIcon :icon="faArrowsRotate" fixed-width />
            Reset Metadata
        </GDropdownItemButton>
        <GDropdownItemButton v-if="deprecated" @click="$emit('undeprecate')">
            <FontAwesomeIcon :icon="faTriangleExclamation" fixed-width />
            Un-mark as Deprecated
        </GDropdownItemButton>
        <GDropdownItemButton v-else @click="$emit('deprecate')">
            <FontAwesomeIcon :icon="faTriangleExclamation" fixed-width />
            Mark as Deprecated
        </GDropdownItemButton>
    </ActionMenu>
</template>
