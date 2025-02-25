<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { type ROCrateZip } from "ro-crate-zip-explorer";

interface Props {
    roCrateZip?: ROCrateZip;
}

defineProps<Props>();
</script>

<template>
    <div v-if="roCrateZip" class="rocrate-explorer">
        {{ roCrateZip.crate.context }}
    </div>
    <BAlert v-else variant="danger" show> No RO-Crate file or URL provided. </BAlert>
</template>
