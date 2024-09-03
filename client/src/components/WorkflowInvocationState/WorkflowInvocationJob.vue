<script setup lang="ts">
import { faClock as faRegClock } from "@fortawesome/free-regular-svg-icons";
import { faClock } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { JobBaseModel } from "@/api/jobs";

import { getJobDuration } from "../JobInformation/utilities";
import { NON_TERMINAL_STATES } from "./util";

import JobInformation from "../JobInformation/JobInformation.vue";
import JobParameters from "../JobParameters/JobParameters.vue";
import UtcDate from "../UtcDate.vue";

const props = defineProps<{
    job: JobBaseModel;
}>();

const jobDuration = getJobDuration(props.job) || null;
</script>

<template>
    <div>
        <div class="d-flex justify-content-between pb-1 pr-1">
            <i>
                <FontAwesomeIcon :icon="faRegClock" class="mr-1" />run
                <UtcDate :date="props.job.create_time" mode="elapsed" />
            </i>
            <i v-if="!NON_TERMINAL_STATES.includes(props.job.state) && jobDuration">
                <FontAwesomeIcon :icon="faClock" class="mr-1" />completed in
                {{ jobDuration }}
            </i>
        </div>
        <JobInformation :job_id="props.job.id" />
        <p></p>
        <JobParameters :job-id="props.job.id" :include-title="false" />
    </div>
</template>
