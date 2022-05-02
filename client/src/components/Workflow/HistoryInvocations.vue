<template>
    <CurrentUser v-slot="{ user }">
        <Invocations
            v-if="user.id && historyName"
            :user-id="user.id"
            :history-id="historyId"
            :history-name="historyName" />
    </CurrentUser>
</template>
<script>
import Invocations from "components/Workflow/Invocations";
import CurrentUser from "components/providers/CurrentUser";
import { mapGetters } from "vuex";

export default {
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
    components: {
        CurrentUser,
        Invocations,
    },
};
</script>
