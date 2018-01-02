<template>
    <div v-cloak>
        <message :message="message" :status="status"></message>
        <h2>Data Manager: {{ dataManagerName + ' - ' + dataManagerDesc }}</h2>
        <div v-if="viewOnly"> Not implemented </div>
        <div> Access managed data by job </div>
        <div v-if="jobs.length > 0">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
		<tr class="header">
		    <td>Actions</td>
		    <td>Job ID</td>
		    <td>User</td>
		    <td>Last Update</td>
		    <td>State</td>
		    <td>Command Line</td>
		    <td>Job Runner</td>
		    <td>PID/Cluster ID</td>
		</tr>
		<tr v-for="job in jobs">
		    <td>
	                <div class="icon-btn-group">
	                    <a class="icon-btn" v-on:click.prevent="viewJobUrl('admin/data_manager/view_job?id=' + job.encoded_id)" title="View info">
	                        <span class="fa fa-info-circle"></span>
	                    </a>
	                    <a class="icon-btn" v-bind:href="setAnchorUrl('tool_runner/rerun?job_id=' + job.encoded_id)" title="Rerun" data-placement="bottom">
	                        <span class="fa fa-refresh"></span>
	                    </a>
	                </div>
                    </td>
                    <td> {{ job.id }} </td>
                    <td> {{ job.history_user_email }} </td>
                    <td> {{ job.update_time }} </td>
                    <td>{{ job.state }}</td>
                    <td>{{ job.command_line }}</td>
                    <td>{{ job.runner_name }}</td>
                    <td>{{ job.runner_external_id }}</td>
		</tr>
            </table>
        </div>
        <div v-else>
            <div class="infomessage">There are no jobs for this data manager.</div>
        </div>   
    </div>
</template>

<script>

import axios from "axios";
import * as mod_toastr from "libs/toastr";
import Message from '../Message.vue';

export default {
    props: {
        dataManagerId: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            dataManagerName: '',
            dataManagerDesc: '',
            jobs: [],
            viewOnly: false,
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
                .get(`${Galaxy.root}data_manager/manage_data_manager?id=${this.dataManagerId}`)
                .then(response => {
                    this._updateManageDataManager(response);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        _updateManageDataManager: function(response) {
            let data = response.data;
            this.dataManagerName = data.data_manager_name;
            this.dataManagerDesc = data.data_manager_description;
            this.jobs = data.jobs;
            this.viewOnly = data.view_only;
            this.message = data.message;
            this.status = data.status;
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        setAnchorUrl: function( url ) {
            return Galaxy.root + url;
        },
        viewJobUrl: function(url) {
            window.location.href = Galaxy.root + url;
        }
    }
}    

</script>

<style>



</style>

