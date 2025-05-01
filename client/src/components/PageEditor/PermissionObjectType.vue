<script setup lang="ts">
import { computed } from "vue";

interface PermissionObjectTypeProps {
    type: "history" | "historyDataset" | "workflow";
}

const props = defineProps<PermissionObjectTypeProps>();

const typeTitle = computed(() => {
    if (props.type == "history") {
        return "历史";
    } else if (props.type == "historyDataset") {
        return "数据集";
    } else {
        return "工作流";
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
