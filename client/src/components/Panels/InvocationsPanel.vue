<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useActivityStore } from "@/stores/activityStore";
import { useUserStore } from "@/stores/userStore";

import InvocationScrollList from "../Workflow/Invocation/InvocationScrollList.vue";
import ActivityPanel from "./ActivityPanel.vue";

const props = defineProps<{
    activityBarId: string;
}>();

const { currentUser } = storeToRefs(useUserStore());
const { toggledSideBar } = storeToRefs(useActivityStore(props.activityBarId));
</script>

<template>
    <ActivityPanel
        title="Workflow Invocations"
        go-to-all-title="Open Invocations List"
        href="/workflows/invocations"
        @goToAll="toggledSideBar = ''">
        <InvocationScrollList v-if="currentUser && !currentUser?.isAnonymous" in-panel />
        <BAlert v-else variant="info" class="mt-3" show>Please log in to view your Workflow Invocations.</BAlert>
    </ActivityPanel>
</template>
