<template>
    <div>
        <table id="destination_parameters" class="tabletip info_data_table">
            <tbody>
                <tr v-for="(value, title) in jobDestinationParams" :key="title">
                    <td>{{ title }}</td>
                    <td>{{ value }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";

export default {
    props: {
        jobId: {
            type: String,
            required: true,
        },
    },
    created: function () {
        this.fetchJobDestinationParams(this.jobId);
    },
    computed: {
        jobDestinationParams: function () {
            return this.$store.getters.jobDestinationParams(this.jobId);
        },
    },
    methods: {
        ...mapCacheActions(["fetchJobDestinationParams"]),
    },
};
</script>
