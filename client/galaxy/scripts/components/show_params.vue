<template>
    <div id="show-dataset-params" class="dataset-metadata" v-cloak>
        <h2>
            {{ toolName }}
        </h2>
        <h3>Dataset Information</h3>
        <table class="tabletip" id="dataset-details">
            <tbody>
                <tr><td> Number:</td><td> {{ hdaData.number }} </td></tr>
                <tr><td> Name:</td><td> {{ hdaData.name }} </td></tr>
                <tr><td> Created:</td><td> {{ hdaData.created_time }} </td></tr>
                <tr><td> Filesize:</td><td> {{ hdaData.file_size }} </td></tr>
                <tr><td> Dbkey:</td><td>{{ hdaData.db_key }} </td></tr>
                <tr><td> Format:</td><td>{{ hdaData.format }} </td></tr>
            </tbody>
        </table>
        <h3>Job Information</h3>
            <table class="tabletip">
                <tbody>
                    <tr v-if="jobData"> <td>Galaxy Tool ID:</td> <td> {{ jobData.tool_id }} </td> </tr>
                    <tr v-if="jobData"> <td>Galaxy Tool Version:</td> <td> {{ jobData.tool_job_version }} </td> </tr>
                    <tr> <td>Tool Version:</td><td> {{ jobData.tool_hda_version }} </td></tr>
                    <tr> <td>Tool Standard Output:</td> <td><a v-bind:href="jobData.tool_std_output">stdout</a></td> </tr>
                    <tr> <td>Tool Standard Error:</td><td><a v-bind:href="jobData.tool_std_error">stderr</a></td> </tr>
                    <tr v-if="jobData"> <td> Tool Exit Code:</td> <td> {{ jobData.tool_exit_code }} </td> </tr>
                    <tr> 
                        <td>History Content API ID:</td>
                        <td> {{ jobData.encoded_hda_id }}
                            <span v-if="jobData.user_is_admin">
                                ({{ jobData.hda_id }})
                            </span>
                        </td>
                    </tr>
                    <tr v-if="jobData">
                        <td>Job API ID:</td>
                        <td> {{ jobData.encoded_job_id }}
                            <span v-if="jobData.user_is_admin">
                                ({{ jobData.job_id }})
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td> History API ID: </td>
                        <td> {{ jobData.encoded_history_id }}
                            <span v-if="jobData.user_is_admin">
                                ({{ jobData.history_id }})
                            </span>
                        </td>
                    </tr>
                    <tr v-if="jobData.hda_dataset_uuid">
                        <td> UUID: </td>
                        <td> {{ jobData.hda_dataset_uuid }} </td>
                    </tr>
                    <tr v-if="jobData.tool_path && !jobData.hda_purged"><td>Full Path:</td><td> {{ jobData.hda_filename }} </td></tr>
                </tbody>
            </table>
    </div>
</template>

<script>

import axios from "axios";

export default {
    props: {
        metadataId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            toolName: "",
            hdaData: {},
            jobData: {}
        };
    },
    created: function() {
        axios
            .get(`${Galaxy.root}datasets/${this.metadataId}/show_params`)
            .then(response => {
                let historyData = response.data;
                this.toolName = historyData.tool_name;
                this.hdaData = historyData.hda;
                this.jobData = historyData.job;
            })
            .catch(e => {
                console.error(e);
            });
    },
}
</script>
