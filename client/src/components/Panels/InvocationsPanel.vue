<script setup lang="ts">
import { storeToRefs } from "pinia";

import { useUserStore } from "@/stores/userStore";

import InvocationScrollList from "../Workflow/Invocation/InvocationScrollList.vue";
import ActivityPanel from "./ActivityPanel.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const { currentUser } = storeToRefs(useUserStore());
</script>

<template>
    <ActivityPanel title="Workflow Invocations" go-to-all-title="Open Invocations List" href="/workflows/invocations">
        <InvocationScrollList v-if="currentUser && !currentUser?.isAnonymous" in-panel />
        <GAlert v-else variant="info" class="mt-3" show>Please log in to view your Workflow Invocations.</GAlert>
    </ActivityPanel>
</template>
