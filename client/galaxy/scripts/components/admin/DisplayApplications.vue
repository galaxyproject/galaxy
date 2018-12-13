<template>
    <div>
        <div v-if="messageVisible" :class="messageClass">
            {{ messageText }}
        </div>
        <div v-if="!applicationsVisible && applicationsLoaded" class="alert alert-warning">
            No display applications available.
        </div>
        <div v-if="applicationsVisible" class="card-header">
            There are currently {{ applicationsLength }}
            <a class="icon-btn" @click.prevent="reloadAll()" title="Reload all display applications" data-placement="bottom">
                <span class="fa fa-refresh"/>
            </a>
            display applications loaded.
        </div>
        <b-table id="display-applications-grid" v-if="applicationsVisible" striped :fields="applicationsAttributes" :items="applications">
            <template slot="reload" slot-scope="data">
                <a class="icon-btn" title="Reload display application" data-placement="bottom" @click.prevent="reload(data.item.id, data.index)">
                    <span class="fa fa-refresh"/>
                </a>
            </template>
            <template slot="links" slot-scope="data">
                <li v-for="link in data.item.links">{{ link.name }}</li>
            </template>
        </b-table>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";

const errorMessageClass = "alert alert-danger";
const infoMessageClass = "alert alert-info";

export default {
    data() {
        return {
            applications: [],
            applicationsLoaded: false,
            applicationsAttributes: [
                { key: 'reload' },
                { key: 'name', sortable: true },
                { key: 'id', sortable: true },
                { key: 'version' },
                { key: 'links' }
            ],
            messageText: null,
            messageClass: null
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
        }
    },
    created() {
        let Galaxy = getGalaxyInstance();
        let url = `${getAppRoot()}api/display_applications`;
        axios
            .get(url)
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
            let url = `${getAppRoot()}api/display_applications/reload`;
            axios
                .post(url, {ids: ids})
                .then(response => {
                    this.messageClass = infoMessageClass;
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
            this.messageClass = errorMessageClass;
        }
    }
};
</script>
