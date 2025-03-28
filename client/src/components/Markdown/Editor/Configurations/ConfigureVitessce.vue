<template>
    <div class="m-2">
        <div class="d-flex flex-row">
            <div class="w-100">
                <div class="h4 mb-1">Attach Data</div>
                <div class="small">Fill in the fields below to map required inputs to this cell.</div>
            </div>
            <CellButton class="align-self-start" title="close" :icon="faTimes" @click="$emit('cancel')" />
        </div>
        <div v-if="true">
            <ConfigureSelector object-id="232323" object-type="history_dataset_id" />
        </div>
        <BAlert v-else variant="warning" show>No datasets found.</BAlert>
    </div>
</template>

<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";

import CellButton from "../CellButton.vue";
import ConfigureSelector from "./ConfigureSelector.vue";

defineProps<{
    name: string;
    content: string;
}>();

defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();
</script>
