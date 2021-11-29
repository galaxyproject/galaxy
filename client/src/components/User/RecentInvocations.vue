<template>
    <invocations
        :invocation-items="invocationItems"
        :loading="loading"
        @reload-invocations="fetchRecentInvocations"
        no-invocations-message="There are no invocations to be shown.">
    </invocations>
</template>

<script>
import Invocations from "../Workflow/Invocations";
import { getRecentInvocations } from "./UserServices";

export default {
    components: {
        Invocations,
    },
    data() {
        return {
            invocationItems: [],
            loading: true,
        };
    },
    created() {
        this.fetchRecentInvocations();
    },
    methods: {
        fetchRecentInvocations() {
            getRecentInvocations()
                .then((response) => {
                    this.invocationItems = response.data;
                    this.loading = false;
                })
                .catch(this.handleError);
        },
        handleError(error) {
            console.error(error);
        },
    },
};
</script>
