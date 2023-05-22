<template>
    <div>
        <InvocationsList
            v-if="currentUser && historyName"
            :user-id="currentUser.id"
            :history-id="historyId"
            :history-name="historyName" />
    </div>
</template>
<script>
import InvocationsList from "components/Workflow/InvocationsList";
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";

export default {
    components: {
        InvocationsList,
    },
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["getHistoryNameById"]),
        historyName() {
            return this.getHistoryNameById(this.historyId);
        },
    },
};
</script>
