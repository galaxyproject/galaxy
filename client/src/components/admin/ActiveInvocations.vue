<template>
    <invocations
        :invocation-items="invocationItems"
        :loading="loading"
        header-message="Workflow invocations that are still being scheduled are displayed on this page."
        no-invocations-message="There are no scheduling workflow invocations to show currently."
        :owner-grid="false">
    </invocations>
</template>

<script>
import Invocations from "../Workflow/Invocations";
import { getActiveInvocations } from "./AdminServices";

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
        getActiveInvocations()
            .then((response) => {
                this.invocationItems = response.data;
                this.loading = false;
            })
            .catch(this.handleError);
    },
    methods: {
        handleError(error) {
            console.error(error);
        },
    },
};
</script>
