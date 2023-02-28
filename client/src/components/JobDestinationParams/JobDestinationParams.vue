<template>
    <div v-if="currentUser.is_admin">
        <h2 class="h-md">Destination Parameters</h2>
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
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

export default {
    props: {
        jobId: {
            type: String,
            required: true,
        },
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        jobDestinationParams: function () {
            return this.$store.getters.jobDestinationParams(this.jobId);
        },
    },
    created: function () {
        this.fetchJobDestinationParams(this.jobId);
    },
    methods: {
        ...mapCacheActions(["fetchJobDestinationParams"]),
    },
};
</script>
