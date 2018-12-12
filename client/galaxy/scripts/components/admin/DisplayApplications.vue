<template>
    <div>
        <div v-if="errorVisible" class="alert alert-danger">
            {{ errorMessage }}
        </div>
        <div v-if="applicationsVisible" class="card-header">
            There are currently {{ applicationsLength }}
            <a class="icon-btn" href="" title="Reload all display applications" data-placement="bottom">
                <span class="fa fa-refresh"/>
            </a>
            display applications loaded.
        </div>
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
            errorMessage: null
        };
    },
    computed: {
        applicationsVisible: function() {
            return this.applications.length > 0;
        },
        applicationsLength: function() {
            return this.applications.length;
        },
        errorVisible: function() {
            return this.error != null;
        }
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
                this.errorMessage = this._errorMessage(e);
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
