<script setup lang="ts">
import { PERMISSIONS_LABELS } from "@/components/Page/constants";

import ObjectPermissions from "./ObjectPermissions.vue";

interface ObjectPermissionsProps {
    markdownContent: string;
}

defineProps<ObjectPermissionsProps>();
</script>

<template>
    <b-modal v-bind="$attrs" :title="PERMISSIONS_LABELS.modalTitle" title-tag="h2" ok-only v-on="$listeners">
        <ObjectPermissions :markdown-content="markdownContent" />
    </b-modal>
</template>
