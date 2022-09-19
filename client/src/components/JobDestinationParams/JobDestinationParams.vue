<template>
    <CurrentUser v-slot="{ user }">
        <div v-if="user.is_admin">
            <h3>Destination Parameters</h3>
            <table id="destination_parameters" class="tabletip info_data_table">
                <tbody>
                    <tr v-for="(value, title) in jobDestinationParams" :key="title">
                        <td>{{ title }}</td>
                        <td>{{ value }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </CurrentUser>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import CurrentUser from "components/providers/CurrentUser";

export default {
    components: {
        CurrentUser,
    },
    props: {
        jobId: {
            type: String,
            required: true,
        },
    },
    computed: {
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
