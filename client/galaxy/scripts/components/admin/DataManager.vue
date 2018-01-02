<template>
    <div v-cloak>
        <message :message="message" :status="status"></message>
        <h2>Data Manager</h2>
        <div v-if="viewOnly"> Not implemented </div>
        <div v-else-if="dataManagers.length == 0">
            <div class="warningmessage">
                <p>You do not currently have any Data Managers installed. You can install some from a <a v-bind:href="setAnchorUrl('admin_toolshed/browse_tool_sheds')" target="galaxy_main">ToolShed</a>.</p>
            </div>
        </div>
        <div v-else>
            <p>Choose your data managing option from below. You may install additional Data Managers from a <a v-bind:href="setAnchorUrl('admin_toolshed/browse_tool_sheds')" target="galaxy_main">ToolShed</a>.
            </p>
            <ul>
                <li><h3>Run Data Manager Tools</h3>
                <div style="margin-left:1em">
                    <ul>
                        <li v-for="dataManager in dataManagers">
                            <a v-bind:href="setAnchorUrl('root?tool_id=' + dataManager.tool_id)" target="_blank">
                                <strong>{{ dataManager.name }}</strong>
                            </a> - {{ dataManager.description }}
                        </li>
                    </ul>
                </div>
                </li>
                <li><h3>View Data Manager Jobs</h3>
                    <div style="margin-left:1em">
                        <ul>
                            <li v-for="dataManager in dataManagers">
                                <a v-on:click.prevent="openUrl('admin/data_manager/manage_data_manager?id=' + dataManager.id)" target="galaxy_main" href="#">
                                    <strong>{{ dataManager.name }}</strong>
                                </a> - {{ dataManager.description }}
                            </li>
                        </ul>
                    </div>
                </li>
                
                <li><h3>View Tool Data Table Entries</h3>
                    <div style="margin-left:1em">
                        <ul>
                            <li v-for="tableName in toolDataTables">
                                <a v-bind:href="setAnchorUrl('data_manager/manage_data_table?table_name=' + tableName)" target="galaxy_main">
                                    <span v-if="managedTableNames.indexOf(tableName) > -1">
                                        <strong> {{ tableName }} </strong> <span class="fa fa-exchange"></span>
                                    </span>
                                    <span v-else>
                                        {{ tableName }}
                                    </span>
                                </a>
                            </li>
                        </ul>
                    </div>
                </li>
            </ul>
        </div>
        <div class="infomessage">
                <p>To find out more information about Data Managers, please visit the
                    <a href="https://galaxyproject.org/admin/tools/data-managers/" target="_blank">wiki.</a>
                </p>
        </div>
    </div>
</template>

<script>

import axios from "axios";
import * as mod_toastr from "libs/toastr";
import Message from '../Message.vue';

export default {
    data() {
        return {
            dataManagers: [],
            toolDataTables: [],
            managedTableNames: [],
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
                .get(`${Galaxy.root}data_manager`)
                .then(response => {
                    this._updateDataManager(response);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        _updateDataManager: function(response) {
            let data = response.data;
            this.dataManagers = data.data_managers;
            this.toolDataTables = data.tool_data_tables;
            this.managedTableNames = data.managed_table_names;
            this.viewOnly = data.view_only;
            this.message = data.message;
            this.status = data.status;;
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        setAnchorUrl: function(url) {
            return Galaxy.root + url;
        },
        openUrl: function(url) {
            window.location.href = Galaxy.root + url;
        }
    }
}    

</script>

<style>



</style>

