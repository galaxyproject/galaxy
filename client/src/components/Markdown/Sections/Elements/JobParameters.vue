<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardFooter, BCardTitle } from "bootstrap-vue";
import { computed, toRef } from "vue";

import { useJobDetails } from "@/composables/jobDetails";
import localize from "@/utils/localization";

import { useMappingJobs } from "./handlesMappingJobs";

import JobSelection from "./JobSelection.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";

interface JobParametersProps {
    jobId?: string;
    implicitCollectionJobsId?: string;
    param?: string;
    title?: string;
    footer?: string;
}

const props = withDefaults(defineProps<JobParametersProps>(), {
    jobId: undefined,
    implicitCollectionJobsId: undefined,
    param: undefined,
    title: undefined,
    footer: undefined,
});

const toolId = computed(() => {
    if (targetJobId.value) {
        return job.value?.tool_id;
    }
    return undefined;
});
const toolVersion = computed(() => {
    if (targetJobId.value) {
        // TODO: `ShowFullJobResponse` does not have a `tool_version` property
        return (job.value as any)?.tool_version;
    }
    return undefined;
});
const jobIdRef = toRef(props, "jobId");
const implicitCollectionJobsIdRef = toRef(props, "implicitCollectionJobsId");

const { selectJobOptions, selectedJob, targetJobId } = useMappingJobs(jobIdRef, implicitCollectionJobsIdRef);

const { job } = useJobDetails(targetJobId, { poll: false });
</script>

<template>
    <BCard nobody>
        <BCardTitle v-if="title">
            <b>{{ title }}</b>
            <GLink v-if="toolId" ref="info" dark thin type="button" :aria-label="localize('Tool details')">
                <FontAwesomeIcon :icon="faInfoCircle" size="sm" />
            </GLink>
            <ToolLinkPopover interactive :target="() => $refs.info" :tool-id="toolId" :tool-version="toolVersion" />
        </BCardTitle>
        <JobSelection
            v-model="selectedJob"
            :job-id="jobId"
            :implicit-collection-jobs-id="implicitCollectionJobsId"
            :select-job-options="selectJobOptions">
            <JobParameters class="job-parameters" :job-id="targetJobId" :param="param" :include-title="false" />
        </JobSelection>
        <BCardFooter v-if="footer">
            {{ footer }}
        </BCardFooter>
    </BCard>
</template>
