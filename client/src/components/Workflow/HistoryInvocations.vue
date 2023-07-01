<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import InvocationsList from "@/components/Workflow/InvocationsList.vue";

interface HistoryInvocationProps {
    historyId: string;
}

const props = defineProps<HistoryInvocationProps>();

const { currentUser } = storeToRefs(useUserStore());
const { getHistoryNameById } = useHistoryStore();
const historyName = computed(() => getHistoryNameById(props.historyId));
</script>
<template>
    <div>
        <InvocationsList
            v-if="currentUser && historyName"
            :user-id="currentUser.id"
            :history-id="historyId"
            :history-name="historyName" />
    </div>
</template>
