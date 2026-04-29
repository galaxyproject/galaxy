<script setup lang="ts">
import { faRedo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute } from "vue-router/composables";

import GButton from "../BaseComponents/GButton.vue";

const route = useRoute();

const props = defineProps<{
    jobId: string;
    outline?: boolean;
}>();

const rerunUrl = computed(() => `/?job_id=${props.jobId}`);
</script>

<template>
    <GButton
        title="Rerun job"
        size="small"
        color="blue"
        :outline="props.outline"
        :transparent="!props.outline"
        :pressed="route.fullPath === rerunUrl"
        :to="rerunUrl">
        <FontAwesomeIcon fixed-width :icon="faRedo" />
        <span>Run Job Again</span>
    </GButton>
</template>
