<template>
    <span>
        <b
            ><a class="generated-export-link" :href="link">{{ link }}</a></b
        >
        <span v-g-tooltip.hover title="Copy export URL to your clipboard">
            <FontAwesomeIcon class="copy-export-link" :icon="faLink" style="cursor: pointer" @click="copyUrl" />
        </span>
        <i
            title="Information about when the history export was generated is included in the job details. Additionally, if there are issues with export, the job details may help figure out the underlying problem or communicate issues to your Galaxy administrator.">
            (<b-link class="show-job-link" href="#" @click="showDetails">view job details</b-link>)
        </i>
        <GModal title="History Export Job" size="medium" :show.sync="details" data-description="job information modal">
            <JobInformation :job-id="historyExport.job_id" :include-times="true" />
        </GModal>
    </span>
</template>

<script>
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { copy } from "@/utils/clipboard";

import GModal from "../BaseComponents/GModal.vue";
import JobInformation from "@/components/JobInformation/JobInformation.vue";

export default {
    components: { GModal, JobInformation, FontAwesomeIcon },
    props: {
        historyExport: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            details: false,
            faLink,
        };
    },
    computed: {
        link() {
            return this.historyExport.external_download_permanent_url;
        },
    },
    methods: {
        showDetails() {
            this.details = true;
        },
        copyUrl() {
            copy(this.link, "Export URL copied to your clipboard");
        },
    },
};
</script>
