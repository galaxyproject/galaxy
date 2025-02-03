<template>
    <div class="p-4 bg-white mb-2">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <div class="h2">Attach Data</div>
                <div class="small">Fill in the fields below to map required inputs to this cell.</div>
            </div>
            <BButton variant="link" class="align-self-start"><FontAwesomeIcon :icon="faTimes" class="fa-lg" /></BButton>
        </div>
        <div class="mb-3">
            <label class="form-label">Workflow</label>
            <input type="text" class="form-control" />
        </div>
        <div class="mb-3">
            <label class="form-label">History Dataset</label>
            <input type="text" class="form-control" />
        </div>
        <div class="d-flex justify-content-end">
            <BButton variant="outline-primary" class="mr-2">Cancel</BButton>
            <BButton variant="outline-primary">OK</BButton>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

defineProps<{}>();

defineEmits<{
    (e: "click"): void;
}>();
</script>
