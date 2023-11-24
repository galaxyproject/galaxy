<script setup lang="ts">
import { computed } from "vue";

import InvocationsList from "@/components/Workflow/InvocationsList.vue";
import { storeToRefs } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";

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
