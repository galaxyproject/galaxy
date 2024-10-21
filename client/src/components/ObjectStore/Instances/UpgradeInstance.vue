<script setup lang="ts">
import { computed, ref } from "vue";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { useInstanceAndTemplate } from "./instance";

import UpgradeForm from "./UpgradeForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    instanceId: string;
}

const props = defineProps<Props>();
const { instance } = useInstanceAndTemplate(ref(props.instanceId));

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();

const latestTemplate = computed(
    () => instance.value && objectStoreTemplatesStore.getLatestTemplate(instance.value?.template_id)
);
</script>
<template>
    <LoadingSpan v-if="!instance || !latestTemplate" message="Loading storage location instance and templates" />
    <UpgradeForm v-else :instance="instance" :latest-template="latestTemplate" />
</template>
