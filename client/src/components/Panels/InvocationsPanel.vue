<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import { useUserStore } from "@/stores/userStore";

import InvocationScrollList from "../Workflow/Invocation/InvocationScrollList.vue";
import ActivityPanel from "./ActivityPanel.vue";

const { currentUser, toggledSideBar } = storeToRefs(useUserStore());

const shouldCollapse = ref(false);
function collapseOnLeave() {
    if (shouldCollapse.value) {
        toggledSideBar.value = "";
    }
}
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/mouse-events-have-key-events -->
    <ActivityPanel
        title="Workflow Invocations"
        go-to-all-title="Open Invocations List"
        href="/workflows/invocations"
        @goToAll="shouldCollapse = true"
        @mouseleave.native="collapseOnLeave">
        <InvocationScrollList
            v-if="currentUser && !currentUser?.isAnonymous"
            in-panel
            @invocation-clicked="shouldCollapse = true" />
        <BAlert v-else variant="info" class="mt-3" show>Please log in to view your Workflow Invocations.</BAlert>
    </ActivityPanel>
</template>
