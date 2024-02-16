<template>
    <b-card v-if="jobs">
        <b-table small caption-top :items="jobsProvider" :fields="fields" primary-key="id" @row-clicked="toggleDetails">
            <template v-slot:row-details="row">
                <JobProvider :id="row.item.id" v-slot="{ item, loading }">
                    <div v-if="loading"><b-spinner label="Loading Job..."></b-spinner></div>
                    <div v-else>
                        <JobInformation v-if="item" :job_id="item.id" />
                        <p></p>
                        <JobParameters v-if="item" :job-id="item.id" :include-title="false" />
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
import BootstrapVue from "bootstrap-vue";
import JobInformation from "components/JobInformation/JobInformation";
import JobParameters from "components/JobParameters/JobParameters";
import { JobProvider } from "components/providers";
import UtcDate from "components/UtcDate";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    components: {
        UtcDate,
        JobProvider,
        JobParameters,
        JobInformation,
    },
    props: {
        jobs: { type: Array, required: true },
    },
    data() {
        return {
            fields: [
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
    },
};
</script>
