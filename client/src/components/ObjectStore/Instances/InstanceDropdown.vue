<script setup lang="ts">
import { computed } from "vue";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { hide } from "./services";
import type { UserConcreteObjectStore } from "./types";

import InstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();

interface Props {
    objectStore: UserConcreteObjectStore;
}

const props = defineProps<Props>();
const routeEdit = computed(() => `/object_store_instances/${props.objectStore.id}/edit`);
const routeUpgrade = computed(() => `/object_store_instances/${props.objectStore.id}/upgrade`);
const isUpgradable = computed(() =>
    objectStoreTemplatesStore.canUpgrade(props.objectStore.template_id, props.objectStore.template_version)
);

async function onRemove() {
    await hide(props.objectStore);
    console.log("HIDING!!!");
}
</script>

<template>
    <InstanceDropdown
        prefix="object-store"
        :name="objectStore.name || ''"
        :is-upgradable="isUpgradable"
        :route-upgrade="routeUpgrade"
        :route-edit="routeEdit"
        @remove="onRemove" />
</template>
