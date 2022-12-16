<template>
    <CurrentUser v-slot="{ user }">
        <InvocationsList
            v-if="user.id && historyName"
            :user-id="user.id"
            :history-id="historyId"
            :history-name="historyName" />
    </CurrentUser>
</template>
<script>
import InvocationsList from "components/Workflow/Invocations";
import CurrentUser from "components/providers/CurrentUser";
import { mapGetters } from "vuex";

export default {
    components: {
        CurrentUser,
        InvocationsList,
    },
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
    computed: {
        ...mapGetters("history", ["getHistoryNameById"]),
        historyName() {
            return this.getHistoryNameById(this.historyId);
        },
    },
};
</script>
