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
                    <tr> <td>Tool Standard Output:</td> <td><a v-bind:href="jobData.tool_std_output" target="_blank">stdout</a></td> </tr>
                    <tr> <td>Tool Standard Error:</td><td><a v-bind:href="jobData.tool_std_error" target="_blank">stderr</a></td> </tr>
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

        <h3>Tool Parameters</h3>
        <table class="tabletip" id="tool-parameters">
            <thead>
                <tr>
                    <th>Input Parameter</th>
                    <th>Value</th>
                    <th>Note for rerun</th>
                </tr>
            </thead>
            <tbody v-html="toolParameterTemplate">
            </tbody>
        </table>
       
        <span v-if="hasParameterErrors"> {{ showError( `One or more of your original parameters may no longer be valid or displayed properly.` ) }} </span>

        <h3>Inheritance Chain</h3>
        <div class="inherit inherit-chain"> {{ hdaData.name }} </div>
        <div v-for="dep in inheritChain">
            <div class="inherit-chain-item">&uarr;</div>
            <div class="inherit">
                {{ dep[0].name }} in {{ dep[1] }} <br/>
            </div>
        </div>

        <div v-if="jobData && jobData.command_line && jobData.tool_path">
            <h3>Command Line</h3>
            <pre class="code"> {{ jobData.command_line }} </pre>
        </div>

        <div v-if="jobMetrics && jobMetrics.expose_metrics">
            <h3>Job Metrics</h3>
            <span v-for="plugin in jobMetrics.plugins">
                <span v-if="jobData.user_is_admin || plugin != 'env'">
                    <h4> {{ plugin }} </h4>
                    <table class="tabletip info_data_table">
                        <tbody>
                            <tr v-for="item in jobMetrics.plugin_metric_displays[ plugin ]">
                                <td> {{ item[ 0 ] }} </td>
                                <td> {{ item[ 1 ] }} </td>
                            </tr>
                        </tbody>
                    </table>
                </span>
            </span>   
        </div>

        <div v-if="jobData && jobData.dependencies && jobData.dependencies.length > 0">
            <h3>Job Dependencies</h3>
            <table class="tabletip">
                <thead>
                    <tr>
                        <th>Dependency</th>
                        <th>Dependency Type</th>
                        <th>Version</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="dependency in jobData.dependencies">
                        <td> {{ dependency['name'] }} </td>
                        <td> {{ dependency['dependency_type'] }} </td>
                        <td> {{ dependency['version'] }} </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div v-if="hdaData.peek">
            <h3>Dataset peek</h3>
            <pre class="dataset-peek"> {{ hdaData.peek }} </pre>
        </div>
    </div>

</template>

<script>

import axios from "axios";
import * as mod_toastr from "libs/toastr";

mod_toastr.options.timeOut = 10000;

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
            jobData: {},
            inheritChain: [],
            jobMetrics: {},
            toolParameterTemplate: "",
            hasParameterErrors: false
        };
    },
    created: function() {
       this.ajaxCall();
    },
    methods: {
        ajaxCall: function() {
            axios
                .get(`${Galaxy.root}datasets/${this.metadataId}/show_params`)
                .then(response => {
                    this._updatePageData(response);
                })
                .catch(e => {
                    this.showError( e );
                });
        },
        _updatePageData: function(response) {
            let historyData = response.data;
            this.toolName = historyData.tool_name;
            this.hdaData = historyData.hda;
            this.jobData = historyData.job;
            this.inheritChain = historyData.inherit_chain;
            this.jobMetrics = historyData.job_metrics;
            this.toolParameterTemplate = historyData.tool_parameter_template;
            this.hasParameterErrors = historyData.has_parameter_errors;
        },
        showError: function( errorMsg ) {
            mod_toastr.error( errorMsg );
        }
    },
    updated: function() {
        let self = this;
        $( '.input-dataset-show-params' ).on( 'click', function( e ) {
            e.preventDefault();
            self.metadataId = $( this ).data( 'hda-id' );
            self.ajaxCall();
            if( window.parent.Galaxy && window.parent.Galaxy.currHistoryPanel ) {
                window.parent.Galaxy.currHistoryPanel.scrollToId( 'dataset-' + self.metadataId );
            }
        });
    }
}
</script>

<style>

.inherit {
    border: 1px solid #bbb;
    padding: 15px;
    text-align: center;
    background-color: #eee;
}

.inherit-chain {
    background-color: #fff;
    font-weight:bold;
}

.inherit-chain-item {
    font-size: 36px;
    text-align: center;
    position: relative;
    top: 3px;
}

table.info_data_table {
        table-layout: fixed;
        word-break: break-word;
    }
    table.info_data_table td:nth-child(1) {
        width: 25%;
    }

</style>

