<script setup lang="ts">
import { computed } from "vue";

interface PermissionObjectTypeProps {
    type: "history" | "historyDataset" | "workflow";
}

const props = defineProps<PermissionObjectTypeProps>();

const typeTitle = computed(() => {
    if (props.type == "history") {
        return "History";
    } else if (props.type == "historyDataset") {
        return "Dataset";
    } else {
        return "Workflow";
    }
});
</script>

<template>
    <span class="object-type">
        {{ typeTitle }}
    </span>
</template>

<style scoped>
.object-type {
    text-decoration: underline;
}
</style>
