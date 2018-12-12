<template>
    <div>
        <div v-if="error" class="alert alert-danger">
            {{ error }}
        </div>
        <div>Display Applications</div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";

export default {
    data() {
        return {
            applications: [],
            error: null
        };
    },
    created() {
        let Galaxy = getGalaxyInstance();
        let url = `${getAppRoot()}api/display_applications`;
        axios
            .get(url)
            .then(response => {
                this.applications = response.data;
            })
            .catch(e => {
                this.error = this._errorMessage(e);
            });
    },
    methods: {
        reload: function() {
        },
        reloadAll: function() {
        },
        _errorMessage: function(e) {
            let message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        }
    }
};
</script>
