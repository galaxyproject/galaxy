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
            hdaData: {}
        };
    },
    created: function() {
        axios
            .get(`${Galaxy.root}datasets/${this.metadataId}/show_params`)
            .then(response => {
                let historyData = response.data;
                this.toolName = historyData.tool_name;
                this.hdaData = historyData.hda;
            })
            .catch(e => {
                console.error(e);
            });
    },
}
</script>
