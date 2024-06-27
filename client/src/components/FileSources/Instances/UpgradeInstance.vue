<script setup lang="ts">
import { computed, ref } from "vue";

import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";

import { useInstanceAndTemplate } from "./instance";

import UpgradeForm from "./UpgradeForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    instanceId: string;
}

const props = defineProps<Props>();
const { instance } = useInstanceAndTemplate(ref(props.instanceId));

const fileSourceTemplatesStore = useFileSourceTemplatesStore();

const latestTemplate = computed(
    () => instance.value && fileSourceTemplatesStore.getLatestTemplate(instance.value?.template_id)
);
</script>
<template>
    <LoadingSpan v-if="!instance || !latestTemplate" message="Loading file source instance and templates" />
    <UpgradeForm v-else :instance="instance" :latest-template="latestTemplate" />
</template>
