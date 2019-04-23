<template>
    <div>
        <b-alert :show="messageVisible" :variant="messageVariant"> {{ messageText }} </b-alert>
        <b-alert :show="warningVisible" variant="warning"> No display applications available. </b-alert>
        <div v-if="applicationsVisible" class="card-header">
            There are currently {{ applicationsLength }}
            <b-button
                size="sm"
                @click.prevent="reloadAll()"
                title="Reload all display applications"
                data-placement="bottom"
            >
                <span class="fa fa-refresh" />
            </b-button>
            display applications loaded.
        </div>
        <b-table
            id="display-applications-grid"
            v-if="applicationsVisible"
            striped
            :fields="applicationsAttributes"
            :items="applications"
        >
            <template slot="reload" slot-scope="data">
                <b-button
                    size="sm"
                    title="Reload display application"
                    data-placement="bottom"
                    @click.prevent="reload(data.item.id, data.index)"
                >
                    <span class="fa fa-refresh" />
                </b-button>
            </template>
            <template slot="links" slot-scope="data">
                <li v-for="link in data.item.links" :key="link.name">{{ link.name }}</li>
            </template>
        </b-table>
    </div>
</template>
<script>
import { getDisplayApplications, reloadDisplayApplications } from "./AdminServices.js";

export default {
    data() {
        return {
            applications: [],
            applicationsLoaded: false,
            applicationsAttributes: [
                { key: "reload" },
                { key: "name", sortable: true },
                { key: "id", sortable: true },
                { key: "version" },
                { key: "links" }
            ],
            messageText: null,
            messageVariant: null
        };
    },
    computed: {
        applicationsIndex: function() {
            let result = {};
            for (let app of this.applications) {
                result[app.id] = app;
            }
            return result;
        },
        applicationsAll: function() {
            let result = [];
            for (let app of this.applications) {
                result.push(app.id);
            }
            return result;
        },
        applicationsVisible: function() {
            return this.applications.length > 0;
        },
        applicationsLength: function() {
            return this.applications.length;
        },
        messageVisible: function() {
            return this.messageText != null;
        },
        warningVisible: function() {
            return !this.applicationsVisible && this.applicationsLoaded;
        }
    },
    created() {
        getDisplayApplications()
            .then(response => {
                this.applications = response.data;
                this.applicationsLoaded = true;
            })
            .catch(e => {
                this._errorMessage(e);
            });
    },
    methods: {
        reload: function(id) {
            this._reload([id]);
        },
        reloadAll: function() {
            let ids = [];
            for (let app of this.applications) {
                ids.push(app.id);
            }
            this._reload(ids);
        },
        _reload: function(ids) {
            this._highlightRows(this.applicationsAll, "default");
            reloadDisplayApplications(ids)
                .then(response => {
                    this.messageVariant = "info";
                    this.messageText = response.data.message;
                    this._highlightRows(response.data.failed, "danger");
                    this._highlightRows(response.data.reloaded, "success");
                })
                .catch(e => {
                    this._errorMessage(e);
                });
        },
        _highlightRows: function(appList, status) {
            for (let appIndex of appList) {
                let app = this.applicationsIndex[appIndex];
                if (app) {
                    app._rowVariant = status;
                }
            }
        },
        _errorMessage: function(e) {
            let message = e && e.response && e.response.data && e.response.data.err_msg;
            this.messageText = message || "Request failed for an unknown reason.";
            this.messageVariant = "danger";
        }
    }
};
</script>
