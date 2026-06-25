<script setup lang="ts">
import { faHdd, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import type { JobBaseModel } from "@/api/jobs.js";
import { useHistoryStore } from "@/stores/historyStore.js";
import { useJobStore } from "@/stores/jobStore.js";

import GCard from "../Common/GCard.vue";
import JobState from "../JobStates/JobState.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const jobsStore = useJobStore();
jobsStore.fetchAllJobs();

const filteredJobs = computed(() => {
	return jobsStore.allJobs.filter((job) => job.tool_id != "__DATA_FETCH__")
}) 

const router = useRouter();

function historyName(historyId: string) {
    const historyStore = useHistoryStore();
    return historyStore.getHistoryNameById(historyId);
}

function cardClicked(job: JobBaseModel) {
    // if (props.inPanel) {
    //     emit("invocation-clicked");
    // }
    router.push(`/jobs/${job.id}/view`);
}

</script>

<template>
	<ActivityPanel
        title="Running jobs"
        go-to-all-title="Open Jobs List"
        href="/workflows/jobs">
		<GCard 
			v-for="job in filteredJobs" 
			:key="job.id"
			clickable
			:title="job.tool_id"
			:title-icon="{icon: faWrench}"
			:update-time="job.update_time"
			@click="() => cardClicked(job)"
		>
		<template v-slot:description>
			<Heading class="m-0" size="text">
				<FontAwesomeIcon :icon="faHdd" fixed-width />

				<small v-if="job.history_id" class="text-muted truncate-n-lines two-lines">
					{{ historyName(job.history_id) }}
				</small>
			</Heading>
		</template>
		<template v-slot:badges>
			<JobState :job="job" />
		</template>
		</GCard>
    </ActivityPanel>

</template>