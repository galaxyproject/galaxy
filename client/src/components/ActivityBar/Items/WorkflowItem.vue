<script setup lang="ts">
import { ref, onMounted, onUnmounted, type Ref } from "vue";
import ActivityItem from "components/ActivityBar/ActivityItem.vue";

const workflows = ref([{
    name: "Show all workflows",
    value: "/workflows/list",
},
{
    name: "Another random 1",
    value: "/workflows/run?id=5114a2a207b7caff",
},
{
    name: "Some random workflow currently noted as static option",
    value: "/workflows/run?id=6fc9fbb81c497f69",
}]);

onMounted(() => {
});

onUnmounted(() => {
});
</script>

<template>
    <ActivityItem
        id="activity-workflow"
        title="Workflow"
        tooltip="Select a Workflow:"
        icon="sitemap"
        :options="workflows" />
</template>
