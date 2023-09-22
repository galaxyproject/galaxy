<template>
    <InvocationsList
        header-message="Workflow invocations that are still being scheduled are displayed on this page."
        no-invocations-message="There are no scheduling workflow invocations to show currently."
        :owner-grid="false">
    </InvocationsList>
</template>

<script>
import InvocationsList from "../Workflow/InvocationsList";

export default {
    components: {
        InvocationsList,
    },
};
</script>
