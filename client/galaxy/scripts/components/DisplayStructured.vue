<template>
    <div v-cloak>
        <div> {{ historyName }} </div>
        <div v-html="historyTemplate">
        </div>
    </div>
</template>

<script>

import axios from "axios";
import * as mod_toastr from "libs/toastr";
import "apps/extended.js";


export default {
    data() {
        return {
            historyName: "",
            historyTemplate: ""
        };
    },
    created: function() {
       this.ajaxCall();
    },
    methods: {
        ajaxCall: function() {
            axios
                .get(`${Galaxy.root}history/display_structured`)
                .then(response => {
                    this._updateHistoryData(response);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        _updateHistoryData: function(response) {
            let historyItems = response.data;
            this.historyName = historyItems.name ? historyItems.name : 'Structure';
            this.historyTemplate = historyItems.template;         
            this.makeHistoryView( historyItems );
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        makeHistoryView: function(historyItems) {
            let historyDict = historyItems.history_json;
            window.hdas = historyDict.map(hda => {
                return new window.bundleEntries.HDAListItemEdit.HDAListItemEdit({
                    model           : new window.bundleEntries.HDAModel.HistoryDatasetAssociation( hda ),
                    el              : $( '#hda-' + hda.id ),
                    linkTarget      : '_self',
                    purgeAllowed    : Galaxy.config.allow_user_dataset_purge,
                    logger          : Galaxy.logger
                }).render( 0 );
            });
            
            $( ".workflow, .tool" ).each(item => {
                var body = $( this ).children( ".body" );
                $( this ).children( ".header" ).click(e => {
                    body.toggle();
                }).addClass( "clickable" );
            });
        }
    }
}    

</script>

<style>

.bold {
    font-weight: bold;
}

.light {
    font-weight: lighter;
    color: grey;
}
.right-aligned {
    text-align: right;
}

.clickable {
    cursor: pointer;
}

.workflow {
    border: solid gray 1px;
}
.workflow > .header {
    background: lightgray;
    padding: 5px 10px;
}
.workflow > .light {
    color: gray;
}
.workflow > .body {
    border-top: solid gray 1px;
}
.workflow > .body > .toolForm {
    border: 0px;
}

div.toolForm {
    border-width        : 1px;
    border-radius       : 0px;
    padding: 5px;
}
.toolForm > .header {
    background-color: #EBD9B2;
    padding: 5px 10px;
}
.workflow div.toolForm:not(:first-child) .header {
    border-top: 1px solid #D6B161;
}
div.toolFormTitle {
    padding: 0px 0px 4px 0px;
    margin: 0px 0px 4px 0px;
    border: 0px;
    background-color: transparent;
    border-bottom: 1px solid #D6B161;
}
/* down from EBD9B2 --> 90743A */
.toolFormTitle > .light {
    color: #90743A;
}
.toolForm em {
    color: #90743A;
}

.job-inputs {
    margin: 0px 6px 0px 6px;
    text-align: left;
}
.job-inputs td:nth-child(1) {
    text-align: right;
    font-weight: lighter;
    color: #90743A;
}
.job-inputs td:nth-child(1):after {
    content : ':'
}
.job-inputs td:nth-child(2) {
    padding-left: 4px;
}
.job-inputs em {
}

.job-inputs-show {
    float: right;
}

.copied-from {
    border: 1px solid lightgrey;
    border-width: 1px 1px 0px 1px;
}
.copied-from .header {
    border-bottom: 1px solid lightgrey;
    padding: 5px;
}
.copied-from .header .bold, .copied-from .header a {
    color: #888;
}

.dataset.hda {
    min-height  : 37px;
    border-width: 0px 0px 1px 0px;
}
.toolFormBody > .dataset.hda:last-child {
    border-bottom-width: 0px;
}
.dataset.hda:first-child {
    border-top: 1px solid #D6B161;
}
.dataset.hda .dataset-title-bar {
    padding-top: 8px;
    padding-left: 10px;
}

</style>

