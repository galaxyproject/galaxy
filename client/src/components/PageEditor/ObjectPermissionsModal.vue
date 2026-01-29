<script setup lang="ts">
import ObjectPermissions from "./ObjectPermissions.vue";

interface ObjectPermissionsProps {
    markdownContent: string;
}

defineProps<ObjectPermissionsProps>();
</script>

<template>
    <b-modal v-bind="$attrs" title="Page Object Permissions" title-tag="h2" ok-only v-on="$listeners">
        <ObjectPermissions :markdown-content="markdownContent" />
    </b-modal>
</template>
