<template>
    <invocations
        :invocationItems="invocationItems" 
        :loading="loading"
        :busy="busy"
        headerMessage="Workflow invocations that are still being scheduled are displayed on this page."
        noInvocationsMessage="There are no scheduling workflow invocations to show currently."
        >
    </invocations>
</template>

<script>
import Invocations from "./Invocations";
import { getActiveInvocations } from "./AdminServices";

export default {
    components: {
        Invocations
    },
    data() {
        return {
            invocationItems: [],
            loading: true,
            busy: true,
        };
    },
    created() {
        getActiveInvocations()
            .then(response => {
                this.invocationItems = response.data;
                this.loading = false;
                this.busy = false;
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
