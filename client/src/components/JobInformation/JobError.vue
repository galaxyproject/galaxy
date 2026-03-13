<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { JobDetails } from "@/api/jobs";

import GLink from "../BaseComponents/GLink.vue";
import GModal from "../BaseComponents/GModal.vue";
import GCard from "../Common/GCard.vue";
import Heading from "../Common/Heading.vue";
import JobInformation from "./JobInformation.vue";

interface Props {
    job: JobDetails;
    header?: string;
}

const props = withDefaults(defineProps<Props>(), {
    header: "Job ended in error",
});

const expanded = ref(false);
const showInfo = ref(false);

const errorClasses = computed(() => {
    const classes = ["code"];
    if (!expanded.value) {
        classes.push("preview");
    }
    return classes;
});

function toggleExpanded() {
    expanded.value = !expanded.value;
}
</script>

<template>
    <GCard :title="props.header" content-class="p-3">
        <template v-slot:description>
            <div v-if="'stderr' in job && job.stderr">
                <div class="d-flex align-items-center flex-gapx-1 py-2">
                    <Heading
                        class="unselectable w-100 mb-0"
                        separator
                        size="sm"
                        :collapse="expanded ? 'open' : 'closed'"
                        @click="toggleExpanded">
                        Job Standard Error
                        <i> ({{ expanded ? "click to collapse" : "click to expand" }}) </i>
                    </Heading>
                    <GLink class="text-nowrap" @click="showInfo = true">
                        See full job details <FontAwesomeIcon :icon="faInfoCircle" />
                    </GLink>
                </div>
                <pre :class="errorClasses">{{ job.stderr }}</pre>
            </div>
            <!-- TODO: modal for reporting error. -->
            <GModal :show.sync="showInfo" class="job-information-modal" size="medium" fixed-height>
                <JobInformation :job-id="job.id" :include-times="true" />
            </GModal>
        </template>
    </GCard>
</template>

<style scoped>
.job-information-modal {
    max-height: 80vh;
}
</style>
