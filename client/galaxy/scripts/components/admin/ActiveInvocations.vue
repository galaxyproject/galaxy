<template>
    <invocations
        :invocationItems="invocationItems"
        :loading="loading"
        headerMessage="Workflow invocations that are still being scheduled are displayed on this page."
        noInvocationsMessage="There are no scheduling workflow invocations to show currently."
        :ownerGrid="false"
    >
    </invocations>
</template>

<script>
import Invocations from "../Workflow/Invocations";
import { getActiveInvocations } from "./AdminServices";

export default {
    components: {
        Invocations
    },
    data() {
        return {
            invocationItems: [],
            loading: true
        };
    },
    created() {
        getActiveInvocations()
            .then(response => {
                this.invocationItems = response.data;
                this.loading = false;
            })
            .catch(this.handleError);
    },
    methods: {
        handleError(error) {
            console.error(error);
        }
    }
};
</script>
