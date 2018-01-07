<template>
    <div v-cloak>
        <message :message="message" :status="status"></message>
        <div v-for="errorText in errorMessages">
            <div v-html="displayErrorMessages(errorText)"></div>
        </div>
        <h2>Data Manager: {{ dataManager.name + ' - ' + dataManager.description }}</h2>
        <div v-if="viewOnly"> Not implemented </div>
        <div v-else>
            <div v-for="(hda, index) in hdas">
	        <table class="tabletip" v-for="hda in hdas">
	            <thead>
		        <tr><th colspan="2" style="font-size: 120%;">
		            Data Manager: 
		            <a v-bind:href="setAnchorUrl('root?tool_id=' + dataManager.tool_id)" target="_blank">
                                <strong>{{ dataManager.name }}</strong>
                            </a> - {{ dataManager.description }}
		            <a class="icon-btn" v-bind:href="setAnchorUrl('tool_runner/rerun?job_id=' + job.encoded_id)" title="Rerun" data-placement="bottom">
	                        <span class="fa fa-refresh"></span>
	                    </a>
		        </th></tr>
	            </thead>
	            <tbody>
	                <tr><td>Name:</td><td> {{ hda.name }} </td></tr>
	           	<tr><td>Created:</td><td>{{ hda.created_time }}</td></tr>
	           	<tr><td>Filesize:</td><td> {{ hda.file_size }}</td></tr>
	           	<tr><td>Tool Exit Code:</td><td> {{ job.exit_code }} </td></tr>
	           	<tr><td>Full Path:</td><td> {{ hda.file_name }} </td></tr>
	           	<tr><td>View complete info:</td><td><a href="#" v-on:click.prevent="showParams(hda.encoded_id)"> {{ hda.id }} </a></td></tr>
	            </tbody>
	        </table>
	        <br />
	        <table class="tabletip" v-for="item in dataManagerOutput[index]">
	            <thead>
		        <tr><th colspan="2" style="font-size: 120%;">
                        Data Table: <a v-bind:href="setAnchorUrl('data_manager/manage_data_table?table_name=' + item.table_name)"> {{ item.table_name }} </a>
                        </th></tr>
	            </thead>
	            <tbody v-for="(table, tableIndex) in item.json_table">
	                <tr v-if="item.json_table.length > 1">
	                    <td><strong>Entry &#35; {{ tableIndex }} </strong></td><td></td>
	                </tr>
	                <tr v-for="tableRow in table">
	                    <td> {{ tableRow.name }}:</td> <td> {{ tableRow.value }} </td>
	                </tr>
	            </tbody>
	        </table>
	        
	    </div>
        </div>
    </div>
</template>

<script>

import axios from "axios";
import * as mod_toastr from "libs/toastr";
import Vue from "vue";
import Message from '../Message.vue';
import ShowParams from "components/ShowParams.vue";

export default {
    props: {
        jobId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            dataManager: '',
            job: [],
            hdas: [],
            viewOnly: false,
            errorMessages: [],
            dataManagerOutput: [],
            message: '',
            status: ''
        };
    },
    components: {
        message: Message,
    },
    created: function() {
       this.ajaxCall();
    },
    methods: {
        ajaxCall: function() {
            axios
                .get(`${Galaxy.root}data_manager/view_job?id=${this.jobId}`)
                .then(response => {
                    this._updateViewJobDataManager(response);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        _updateViewJobDataManager: function(response) {
            let data = response.data;
            this.dataManager = data.data_manager;
            this.job = data.job;
            this.hdas = data.hdas;
            this.viewOnly = data.view_only;
            this.message = data.message;
            this.status = data.status;
            this.errorMessages = data.error_messages;
            this.dataManagerOutput = data.data_manager_output;
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        setAnchorUrl: function( url ) {
            return Galaxy.root + url;
        },
        displayErrorMessages: function(errorText) {
            return '<div class="errormessage"><p>' + errorText + '</p></div>';
        },
        showParams: function(datasetId) {
            let showParamsInstance = Vue.extend(ShowParams),
            mountView = document.createElement("div");
            Galaxy.page.center.display(mountView);
            new showParamsInstance({propsData: { metadataId: datasetId }}).$mount(mountView);
        }
    }
}    

</script>

<style>



</style>

