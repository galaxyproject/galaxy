<script setup lang="ts">
import { faArrowCircleLeft, faArrowCircleRight, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BTable } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { JobBaseModel } from "@/api/jobs";

import { getJobDuration } from "../JobInformation/utilities";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import GModal from "../BaseComponents/GModal.vue";
import Heading from "../Common/Heading.vue";
import JobDetails from "../JobInformation/JobDetails.vue";
import JobState from "../JobStates/JobState.vue";
import UtcDate from "../UtcDate.vue";

const props = defineProps<{
    jobs: JobBaseModel[];
    invocationId: string;
    currentPage: number;
    sortDesc: boolean;
    perPage: number;
}>();

const emit = defineEmits<{
    (e: "update:current-page", value: number): void;
    (e: "update:sort-desc", value: boolean): void;
}>();

const showModal = ref(false);

/** The job currently being viewed in the modal */
const viewedJob = ref<JobBaseModel | null>(null);

/** The computed table index of the job selected for viewing details
 *
 * _Note: Sometimes, if the `viewedJob` doesn't exist in `props.jobs` by now (somehow `props.jobs` has changed
 * since the job was selected), this will be `null` while `viewedJob` will not be null._
 */
const viewedJobIndex = computed<number | null>({
    get() {
        if (viewedJob.value === null) {
            return null;
        }
        return props.jobs.findIndex((job) => job.id === viewedJob.value?.id);
    },
    set(newIndex: number | null) {
        if (newIndex !== null && props.jobs[newIndex]) {
            viewedJob.value = props.jobs[newIndex];
        } else {
            viewedJob.value = null;
        }
    },
});

function getTrClass(job: JobBaseModel) {
    return {
        "clickable-row": true,
        "font-weight-bold": job.id === viewedJob.value?.id,
    };
}

function jobClicked(job: JobBaseModel) {
    viewedJob.value = job;
    showModal.value = true;
}

function onSort(sortInfo: { sortDesc: boolean }) {
    emit("update:sort-desc", sortInfo.sortDesc);
}

function navigateJob(direction: "previous" | "next") {
    if (viewedJobIndex.value === null || viewedJob.value === null || !props.jobs.length) {
        return;
    }
    if (viewedJobIndex.value === 0 && direction === "previous") {
        viewedJobIndex.value = props.jobs.length - 1;
    } else if (viewedJobIndex.value === props.jobs.length - 1 && direction === "next") {
        viewedJobIndex.value = 0;
    } else {
        viewedJobIndex.value += direction === "next" ? 1 : -1;
    }
}

// If we navigate to a job not on the current page, switch to that page
watch(
    () => viewedJobIndex.value,
    (newIndex) => {
        if (newIndex !== null) {
            const pageOfJob = Math.floor(newIndex / props.perPage) + 1;
            if (pageOfJob !== props.currentPage) {
                emit("update:current-page", pageOfJob);
            }
        }
    },
);

// If the number of jobs changes such that the current page is out of range, adjust the current page
watch(
    () => props.jobs.length,
    (newLength) => {
        const maxPage = Math.ceil(newLength / props.perPage) || 1;
        if (props.currentPage > maxPage) {
            emit("update:current-page", maxPage);
        }
    },
);
</script>

<template>
    <div>
        <BTable
            class="job-step-jobs"
            primary-key="id"
            :current-page="props.currentPage"
            :items="props.jobs"
            striped
            no-sort-reset
            no-local-sorting
            hover
            :per-page="props.perPage"
            :fields="[
                { key: 'id', label: 'Job ID' },
                { key: 'tool_id', label: 'Tool' },
                { key: 'update_time', label: 'Updated', sortable: true },
                { key: 'duration', label: 'Time To Finish' },
                { key: 'state', label: 'State' },
            ]"
            :tbody-tr-class="getTrClass"
            @row-clicked="jobClicked"
            @sort-changed="onSort">
            <template v-slot:cell(id)="data">
                <div class="d-flex flex-gapx-1 align-items-center">
                    <span>{{ data.item.id }}</span>

                    <GButton
                        icon-only
                        size="small"
                        title="View Job in New Tab"
                        :href="`/jobs/${data.item.id}/view`"
                        target="_blank"
                        rel="noopener">
                        <FontAwesomeIcon :icon="faExternalLinkAlt" />
                    </GButton>
                </div>
            </template>

            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.item.update_time" mode="timeonly" />
            </template>

            <template v-slot:cell(state)="data">
                <JobState :job="data.item" />
            </template>

            <template v-slot:cell(duration)="data">
                {{ getJobDuration(data.item) }}
            </template>
        </BTable>

        <GModal :show.sync="showModal" fixed-height size="medium" @close="viewedJob = null">
            <template v-slot:header>
                <div v-if="viewedJob" class="w-100 d-flex justify-content-between align-items-center">
                    <div class="d-flex flex-gapx-1 align-items-center">
                        <Heading h2 size="sm" style="margin-bottom: 0">
                            Job
                            <code>
                                {{ viewedJob.id }}
                            </code>
                        </Heading>

                        <JobState :job="viewedJob" />
                    </div>

                    <div class="d-flex align-items-center">
                        <GButtonGroup>
                            <GButton transparent @click="navigateJob('previous')">
                                <FontAwesomeIcon :icon="faArrowCircleLeft" />
                                Prev
                            </GButton>
                            <GButton transparent @click="navigateJob('next')">
                                <FontAwesomeIcon :icon="faArrowCircleRight" />
                                Next
                            </GButton>
                        </GButtonGroup>
                    </div>
                </div>
            </template>
            <JobDetails v-if="viewedJob" :job-id="viewedJob.id" :invocation-id="invocationId" />
        </GModal>
    </div>
</template>

<style scoped lang="scss">
.job-step-jobs {
    :deep(.clickable-row) {
        cursor: pointer;
        color: var(--color-blue-600);
        user-select: text;

        &:hover {
            td {
                text-decoration: underline;
            }

            // No underline on the `JobState` badge
            td:last-child {
                text-decoration: none !important;
            }
        }
    }
}
</style>
