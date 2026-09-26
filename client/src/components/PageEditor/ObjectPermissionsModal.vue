<script setup lang="ts">
import { computed } from "vue";

import { PERMISSIONS_LABELS } from "@/components/Page/constants";

import GModal from "../BaseComponents/GModal.vue";
import ObjectPermissions from "./ObjectPermissions.vue";

interface ObjectPermissionsProps {
    markdownContent: string;
    show: boolean;
}

const props = defineProps<ObjectPermissionsProps>();

const emit = defineEmits<{
    (e: "update:show", show: boolean): void;
}>();

/** Computed toggle that handles showing and hiding the modal */
const localShowToggle = computed({
    get: () => props.show,
    set: (value: boolean) => {
        emit("update:show", value);
    },
});
</script>

<template>
    <GModal :show.sync="localShowToggle" :title="PERMISSIONS_LABELS.modalTitle" size="small">
        <ObjectPermissions :markdown-content="markdownContent" />
    </GModal>
</template>
