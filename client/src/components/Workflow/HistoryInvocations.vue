<template>
    <div>
        <InvocationsList
            v-if="currentUser.id && historyName"
            :user-id="currentUser.id"
            :history-id="historyId"
            :history-name="historyName" />
    </div>
</template>
<script>
import InvocationsList from "components/Workflow/InvocationsList";
import { mapGetters } from "vuex";
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

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
        ...mapGetters("history", ["getHistoryNameById"]),
        historyName() {
            return this.getHistoryNameById(this.historyId);
        },
    },
};
</script>
