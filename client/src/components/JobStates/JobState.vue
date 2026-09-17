<script setup lang="ts">
import { faSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, toRef } from "vue";

import { isRegisteredUser } from "@/api";
import { deleteJob, NON_TERMINAL_STATES } from "@/api/jobs";
import { useJobDetails } from "@/composables/jobDetails.js";
import { useToast } from "@/composables/toast";
import { getHeaderClass, iconClasses } from "@/composables/useInvocationGraph";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "../BaseComponents/GButton.vue";

const props = defineProps<{
    jobId: string;
}>();

const badgeClass = computed(() => {
    if (!job.value) {
        return {};
    }
    return {
        ...getHeaderClass(job.value.state),
        "text-center": true,
    };
});

const { job } = useJobDetails(toRef(props, "jobId"));

const stateIcon = computed(() => (job.value ? iconClasses[job.value.state] : null));

const Toast = useToast();

const { currentUser } = storeToRefs(useUserStore());

/** Whether the current user owns the job (can stop it) */
const userOwnsJob = computed(() => {
    if (!job.value || !currentUser.value || !isRegisteredUser(currentUser.value)) {
        return false;
    }
    if ("user_id" in job.value && job.value.user_id) {
        return job.value.user_id === currentUser.value.id;
    }
    // `user_id` not available on `JobBaseModel` — caller context implies ownership
    return true;
});

/** Whether to render this button
 * 1. If the job is not the user's own
 * 2. Job is not in a terminal state
 * 3. Job is not an upload or data fetch tool
 *    (actually decided based on if the tool `is_workflow_compatible`,
 *    but that would require an extra fetch. Just going by known non-rerunnable tool ids for now)
 */
const canStopJob = computed(
    () =>
        job.value &&
        userOwnsJob.value &&
        NON_TERMINAL_STATES.includes(job.value.state) &&
        !job.value.tool_id.startsWith("upload") &&
        job.value.tool_id !== "__DATA_FETCH__",
);

/** Whether the stop job action is currently being performed */
const stopping = ref(false);

async function stopJob() {
    if (!job.value || stopping.value) {
        return;
    }
    stopping.value = true;
    try {
        await deleteJob(job.value.id);

        Toast.success("Job scheduled to be stopped.");
    } catch (error) {
        Toast.error(errorMessageAsString(error), "Failed to stop the job.");
    } finally {
        stopping.value = false;
    }
}
</script>

<template>
    <span v-if="job" class="job-state-badge rounded px-2 py-1 text-nowrap" :class="badgeClass">
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
        {{ job.state }}
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
