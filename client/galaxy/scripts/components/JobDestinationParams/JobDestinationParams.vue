<template>
    <div>
        <table class="tabletip info_data_table">
            <tbody>
            <tr v-for="(value, title) in destinationParams">
                <td>{{ title }}</td>
                <td>{{ value }}</td>
            </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
    import {mapCacheActions} from "vuex-cache";
    import {mapGetters} from "vuex";

    export default {
        props: {
            jobId: {
                type: String,
            },
            datasetId: {
                type: String,
            },
            datasetType: {
                type: String,
                default: "hda",
            },
            includeTitle: {
                type: Boolean,
                default: true,
            },
        },
        data() {
            return {};
        },
        created: function () {
            this.fetchJobDestinationParams(this.jobId);
        },
        computed: {
            ...mapGetters(["getJobDestinationParams"]),
            jobDestinationParams: function () {
                return this.getJobDestinationParams(this.jobId);
            },
            destinationParams: function () {
                const params = this.jobDestinationParams;
                const special_parameters = {
                    'runner_name': 'Runner',
                    'runner_external_id': 'Runner Job ID',
                    'handler': 'Handler'
                };

                Object.keys(params).forEach((title) => {
                    if (title in special_parameters) {
                        params[title] = special_parameters[title]
                    }
                });
                return params;
            }
        },
        methods: {
            ...mapCacheActions(["fetchJobDestinationParams"]),
        },
    };
</script>
