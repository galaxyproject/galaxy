<script setup lang="ts">
import { faSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { type JobBaseModel, NON_TERMINAL_STATES } from "@/api/jobs";
import { useToast } from "@/composables/toast";
import { getHeaderClass, iconClasses } from "@/composables/useInvocationGraph";

import GButton from "../BaseComponents/GButton.vue";

const props = defineProps<{
    job: JobBaseModel;
}>();

const badgeClass = computed(() => {
    return {
        ...getHeaderClass(props.job.state),
        "text-center": true,
    };
});

const stateIcon = computed(() => iconClasses[props.job.state] || null);

const Toast = useToast();

/** Whether the current user owns the job (can stop it) */
const userOwnsJob = computed(() => {
    return true; // TODO: For testing i have true, will have proper implementation later
});

/** Whether to render this button
 * 1. If the job is not the user's own
 * 2. Job is not in a terminal state
 */
const canStopJob = computed(() => userOwnsJob.value && NON_TERMINAL_STATES.includes(props.job.state));

/** Whether the stop job action is currently being performed */
const stopping = ref(false);

async function stopJob() {
    stopping.value = true;
    try {
        // TODO: To be implemented: Call the API to stop the job, and handle any errors that may occur.
        //      Ideally, we would want a job object returned from the API after stopping,
        //      and we would want to update the job state in the UI accordingly. For now, I am just
        //      using a Toast.

        Toast.success("Job stopped successfully.");

        // TODO: Handle job state returned by the API
    } catch (error) {
        // TODO: Handle string errorMessageAsString, just casting to string for now
        Toast.error(error as string, "Failed to stop the job.");
    } finally {
        stopping.value = false;
    }
}
</script>

<template>
    <span class="job-state-badge rounded px-2 py-1 text-nowrap" :class="badgeClass">
        <FontAwesomeIcon
            v-if="stateIcon"
            :icon="stateIcon.icon"
            :spin="stateIcon.spin"
            :class="{ 'hoverable-icon': canStopJob }" />
        <GButton
            v-if="canStopJob"
            transparent
            inline
            icon-only
            pill
            size="small"
            class="stop-job-btn"
            title="Stop the execution of this job"
            :disabled="stopping"
            disabled-title="Stopping job..."
            @click.stop.prevent="stopJob">
            <FontAwesomeIcon :icon="faSquare" />
        </GButton>
        {{ props.job.state }}
    </span>
</template>

<style lang="scss" scoped>
// If the job is in a stoppable state, we want to make the default state
// icon hide on hover, and show the stop button instead.
.job-state-badge {
    position: relative;

    &:hover {
        .hoverable-icon {
            visibility: hidden;
        }
        .stop-job-btn {
            display: inline-block;
        }
    }
}

.stop-job-btn {
    display: none;
    position: absolute;
    left: 0.5rem;
    top: 50%;
    transform: translateY(-50%);
    height: 1em;
    width: 1em;
    line-height: 1;
    padding: 0 !important;
    min-height: unset !important;
}

.hoverable-icon {
    display: inline-block;
    height: 1em;
    width: 1em;
    line-height: 1;
}

// When canStopJob is true, ensure only one shows at a time
.job-state-badge:not(:hover) .stop-job-btn {
    display: none;
}

.job-state-badge:hover .hoverable-icon {
    visibility: hidden;
}
</style>
