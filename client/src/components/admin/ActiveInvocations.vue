<template>
    <invocations
        header-message="Workflow invocations that are still being scheduled are displayed on this page."
        no-invocations-message="There are no scheduling workflow invocations to show currently."
        :owner-grid="false">
    </invocations>
</template>

<script>
import Invocations from "../Workflow/Invocations";

export default {
    components: {
        Invocations,
    },
};
</script>
