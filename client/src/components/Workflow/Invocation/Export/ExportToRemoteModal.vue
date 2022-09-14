<script setup>
import { computed, ref } from "vue";
import { BModal } from "bootstrap-vue";
import { InvocationExportPlugin } from "./model";

const modal = ref(null);

const props = defineProps({
    exportPlugin: { type: InvocationExportPlugin, required: true },
    invocationId: { type: String, required: true },
    writableFileSources: { type: Array, required: true },
});

const title = computed(() => `Export ${props.exportPlugin.title} to remote file source`);

function showModal() {
    modal.value.show();
}

defineExpose({ showModal });
</script>

<template>
    <b-modal ref="modal" :title="title">
        <div v-for="(v, i) in writableFileSources" :key="i">
            {{ v.label }}
        </div>
    </b-modal>
</template>
