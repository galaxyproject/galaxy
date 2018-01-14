<template>
    <div v-cloak>
        <div>
        </div>
    </div>
</template>

<script>

import axios from "axios";
import * as mod_toastr from "libs/toastr";


export default {
    props: {
        id: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            historyDict: {},
            userIsOwner: false,
            historyIsCurrent: false,
            showDeleted: false,
            showHidden: false
        };
    },
    created: function() {
       this.ajaxCall();
    },
    methods: {
        ajaxCall: function() {
            axios
                .get(`${Galaxy.root}history/view/${this.id}`)
                .then(response => {
                    this._updateHistoryView(response);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        _updateHistoryView: function(response) {
            let history = response.data;
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        makeHistoryView: function() {
            
        }
    },
    updated: function() {
    
    }
}    

</script>

<style>

#history-view-controls {
    flex: 0 0 44px;
    background-color: white;
    border-bottom: 1px solid #DDD;
    width: 100%;
    padding: 8px;
}
.history-panel > .controls .title {
    font-size: 120%;
}
.history-panel > .controls .title input {
    font-size: 100%;
}
a.btn {
    text-decoration: none;
}

</style>

