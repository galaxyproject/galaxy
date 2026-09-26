<script setup lang="ts">
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { JobExportHistoryArchiveModel } from "@/api/histories.export";
import { copy } from "@/utils/clipboard";

import GLink from "../BaseComponents/GLink.vue";
import GModal from "../BaseComponents/GModal.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";

const props = defineProps<{
    historyExport: JobExportHistoryArchiveModel;
}>();

const details = ref(false);
const link = computed(() => props.historyExport.external_download_permanent_url);
</script>

<template>
    <span>
        <GLink class="generated-export-link" :href="link">{{ link }}</GLink>
        <span v-g-tooltip.hover title="Copy export URL to your clipboard">
            <FontAwesomeIcon
                class="copy-export-link"
                :icon="faLink"
                style="cursor: pointer"
                @click="() => copy(link, 'Export URL copied to your clipboard')" />
        </span>
        <i
            title="Information about when the history export was generated is included in the job details. Additionally, if there are issues with export, the job details may help figure out the underlying problem or communicate issues to your Galaxy administrator.">
            (<GLink class="font-italic show-job-link" thin @click="() => (details = true)">view job details</GLink>)
        </i>
        <GModal title="History Export Job" size="medium" :show.sync="details" data-description="job information modal">
            <JobInformation :job-id="historyExport.job_id" :include-times="true" />
        </GModal>
    </span>
</template>
