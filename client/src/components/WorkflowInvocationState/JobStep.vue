<template>
    <b-card v-if="jobs">
        <b-table
            small
            caption-top
            :items="jobsProvider"
            :fields="fields"
            primary-key="id"
            :tbody-tr-class="showingJobCls"
            :striped="!invocationGraph"
            @row-clicked="rowClicked">
            <template v-slot:cell(showing_job)="data">
                <span v-if="showingJobId === data.item.id || data.item._showDetails">
                    <FontAwesomeIcon v-if="!invocationGraph" icon="caret-down" size="lg" />
                    <span v-else>
                        <FontAwesomeIcon class="text-primary" icon="fa-eye" />
                    </span>
                </span>
                <span v-else>
                    <FontAwesomeIcon v-if="!invocationGraph" icon="caret-right" size="lg" />
                    <span v-else>
                        <FontAwesomeIcon icon="fa-eye" />
                    </span>
                </span>
            </template>
            <template v-slot:row-details="row">
                <JobProvider :id="row.item.id" v-slot="{ item, loading }">
                    <div v-if="loading"><b-spinner label="Loading Job..."></b-spinner></div>
                    <div v-else>
                        <b-card>
                            <JobInformation v-if="item" :job_id="item.id" />
                            <p></p>
                            <JobParameters v-if="item" :job-id="item.id" :include-title="false" />
                        </b-card>
                    </div>
                </JobProvider>
            </template>
            <template v-slot:cell(create_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </b-table>
    </b-card>
</template>
<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import JobInformation from "components/JobInformation/JobInformation";
import JobParameters from "components/JobParameters/JobParameters";
import { JobProvider } from "components/providers";
import UtcDate from "components/UtcDate";
import Vue from "vue";

Vue.use(BootstrapVue);
library.add(faCaretDown, faCaretRight);

export default {
    components: {
        FontAwesomeIcon,
        UtcDate,
        JobProvider,
        JobParameters,
        JobInformation,
    },
    props: {
        jobs: { type: Array, required: true },
        invocationGraph: { type: Boolean, default: false },
        showingJobId: { type: String, default: null },
    },
    data() {
        return {
            fields: [
                { key: "showing_job", label: "", sortable: false },
                { key: "state", sortable: true },
                { key: "update_time", label: "Updated", sortable: true },
                { key: "create_time", label: "Created", sortable: true },
            ],
            toggledItems: {},
        };
    },
    methods: {
        jobsProvider(ctx, callback) {
            // It may seem unnecessary to use a provider here, since the jobs prop
            // is being updated externally. However we need to keep track of the
            // _showDetails attribute which determines whether the row is shown as expanded
            this.$watch(
                "jobs",
                function () {
                    // update new jobs array with current state
                    const toggledJobs = this.jobs.map((e) => {
                        return { ...e, _showDetails: !!this.toggledItems[e.id] };
                    });
                    callback(toggledJobs);
                },
                { immediate: true }
            );
            return null;
        },
        toggleDetails(item) {
            // toggle item
            item._showDetails = !item._showDetails;
            // update state
            this.toggledItems[item.id] = item._showDetails;
        },
        rowClicked(item) {
            if (this.invocationGraph) {
                this.$emit("row-clicked", item.id);
            } else {
                this.toggleDetails(item);
            }
        },
        showingJobCls(item, type) {
            let cls = "job-tr-class cursor-pointer unselectable";
            if (this.showingJobId === item.id) {
                cls += " showing-job";
            }
            return cls;
        },
    },
};
</script>

<style lang="scss">
// NOTE: Couldn't use scoped style due to it not working for the BTable class rows
@import "theme/blue.scss";
@import "base.scss";

// Table row class
.job-tr-class {
    &:hover {
        background-color: $brand-secondary;
    }
    &.showing-job {
        background-color: darken($brand-secondary, 10%);
    }
    &:not(.showing-job) {
        border-top: 0.2rem solid $brand-secondary;
    }
}
</style>
