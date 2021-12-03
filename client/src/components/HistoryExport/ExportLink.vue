<template>
    <span>
        <b
            ><a class="generated-export-link" :href="link">{{ link }}</a></b
        >
        <font-awesome-icon
            v-b-tooltip.hover
            title="Copy export URL to your clipboard"
            class="copy-export-link"
            icon="link"
            style="cursor: pointer"
            @click="copyUrl" />
        <i
            title="Information about when the history export was generated is included in the job details. Additionally, if there are issues with export, the job details may help figure out the underlying problem or communicate issues to your Galaxy administrator.">
            (<b-link class="show-job-link" href="#" @click="showDetails">view job details</b-link>)
        </i>
        <b-modal v-model="details" modal-class="job-information-modal" scrollable ok-only hide-header>
            <job-information :job_id="historyExport.job_id" :include-times="true" />
        </b-modal>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { BModal } from "bootstrap-vue";
import { copy } from "utils/clipboard";
import JobInformation from "components/JobInformation/JobInformation.vue";

library.add(faLink);

export default {
    components: { BModal, JobInformation, FontAwesomeIcon },
    props: {
        historyExport: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            details: false,
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
