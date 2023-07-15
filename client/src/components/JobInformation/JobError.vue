<template>
    <GCard border-variant="danger" :header="header">
        <GCardText>
            <div @click="showInfo = true">
                <a href="#">See full job details <FontAwesomeIcon icon="info-circle" /></a>
            </div>
            <div v-if="job.stderr" class="error-wrapper" @click="toggleExpanded">
                Job Standard Error
                <pre :class="errorClasses">{{ job.stderr }}</pre>
                <b v-if="!expanded">(Click to expand job standard error)</b>
            </div>
            <!-- TODO: modal for reporting error. -->
        </GCardText>
        <b-modal v-model="showInfo" modal-class="job-information-modal" scrollable ok-only hide-header>
            <JobInformation :job_id="job.id" :include-times="true" />
        </b-modal>
    </GCard>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import JobInformation from "./JobInformation.vue";
import GCard from "@/component-library/GCard.vue";
import GCardText from "@/component-library/GCardText.vue";

library.add(faInfoCircle);
Vue.use(BootstrapVue);

export default {
    components: {
        GCard,
        GCardText,
        JobInformation,
        FontAwesomeIcon,
    },
    props: {
        job: {
            type: Object,
            required: true,
        },
        header: {
            type: String,
            default: "Job ended in error",
        },
    },
    data() {
        return {
            expanded: false,
            showInfo: false,
        };
    },
    computed: {
        errorClasses() {
            const classes = ["code"];
            if (!this.expanded) {
                classes.push("preview");
            }
            return classes;
        },
    },
    methods: {
        toggleExpanded() {
            this.expanded = !this.expanded;
        },
    },
};
</script>

<style scoped>
.error-wrapper {
    margin-top: 10px;
}
</style>
