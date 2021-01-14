<template>
    <b-card v-if="jobs">
        <b-table
            small
            caption-top
            :items="jobs"
            :fields="fields"
            v-if="jobs"
            @row-clicked="(item) => $set(item, '_showDetails', !item._showDetails)"
        >
            <template v-slot:row-details="row">
                <job-provider
                    :id="row.item.id"
                    v-slot="{
                        item,
                        loading,
                    }"
                >
                    <div v-if="loading"><b-spinner label="Loading Job..."></b-spinner></div>
                    <div v-else>
                        <job-information :job_id="item.id" v-if="item" />
                        <p></p>
                        <job-parameters v-if="item" :jobId="item.id" :includeTitle="false" />
                    </div>
                </job-provider>
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
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { JobProvider } from "./providers";
import JobInformation from "components/JobInformation/JobInformation";
import JobParameters from "components/JobParameters/JobParameters";
import UtcDate from "components/UtcDate";

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
        };
    },
};
</script>
