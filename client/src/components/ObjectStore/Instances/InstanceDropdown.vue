<script setup lang="ts">
import { computed } from "vue";

import { GalaxyApi } from "@/api";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { rethrowSimple } from "@/utils/simple-error";

import type { UserConcreteObjectStore } from "./types";

import InstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();

interface Props {
    objectStore: UserConcreteObjectStore;
}

const props = defineProps<Props>();
const routeEdit = computed(() => `/object_store_instances/${props.objectStore.uuid}/edit`);
const routeUpgrade = computed(() => `/object_store_instances/${props.objectStore.uuid}/upgrade`);
const isUpgradable = computed(() =>
    objectStoreTemplatesStore.canUpgrade(props.objectStore.template_id, props.objectStore.template_version)
);

async function onRemove() {
    const { error } = await GalaxyApi().PUT("/api/object_store_instances/{uuid}", {
        params: { path: { uuid: props.objectStore.uuid } },
        body: { hidden: true },
    });

    if (error) {
        rethrowSimple(error);
    }

    emit("entryRemoved");
}

const emit = defineEmits<{
    (e: "entryRemoved"): void;
    (e: "test"): void;
}>();
</script>

<template>
    <InstanceDropdown
        prefix="object-store"
        :name="objectStore.name || ''"
        :is-upgradable="isUpgradable"
        :route-upgrade="routeUpgrade"
        :route-edit="routeEdit"
        @test="emit('test')"
        @remove="onRemove" />
</template>
