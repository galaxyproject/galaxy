<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-3">
            <b-link :href="repo.repository_url" target="_blank">Show additional details and dependencies.</b-link>
        </div>
        <installationstates :repo="repo" :toolshedUrl="toolshedUrl" />
    </b-card>
</template>
<script>
import InstallationStates from "./InstallationStates.vue";
export default {
    components: {
        installationstates: InstallationStates
    },
    props: ["repo", "toolshedUrl"]
};
</script>
