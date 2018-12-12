<template>
    <div>
        <div v-if="messageVisible" :class="messageClass">
            {{ messageText }}
        </div>
        <div v-if="applicationsVisible" class="card-header">
            There are currently {{ applicationsLength }}
            <a class="icon-btn" @click.prevent="reloadAll()" title="Reload all display applications" data-placement="bottom">
                <span class="fa fa-refresh"/>
            </a>
            display applications loaded.
        </div>
        <table v-if="applicationsVisible" class="table table-striped">
            <thead>
                <tr>
                    <th>Reload</th>
                    <th>Name</th>
                    <th>Identifier</th>
                    <th>Version</th>
                    <th>Links</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="app in applications">
                    <td>
                        <a class="icon-btn" href="" title="Reload display application" data-placement="bottom" @click.prevent="reload(app.id)">
                            <span class="fa fa-refresh"/>
                        </a>
                    </td>
                    <td>{{ app.name }}</td>
                    <td>{{ app.id }}</td>
                    <td>{{ app.version }}</td>
                    <td>
                        <ul>
                            <li v-for="link in app.links">{{ link.name }}</li>
                        </ul>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";

const errorMessageClass = "alert alert-danger";
const successMessageClass = "alert alert-info";

export default {
    data() {
        return {
            applications: [],
            messageText: null,
            messageClass: null
        };
    },
    computed: {
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
            let url = `${getAppRoot()}api/display_applications/reload`;
            axios
                .post(url, {ids: ids})
                .then(response => {
                    this.messageText = response && response.data && response.data.message;
                    this.messageClass = successMessageClass;
                })
                .catch(e => {
                    this._errorMessage(e);
                });
        },
        _errorMessage: function(e) {
            let message = e && e.response && e.response.data && e.response.data.err_msg;
            this.messageText = message || "Request failed for an unknown reason.";
            this.messageClass = errorMessageClass;
        }
    }
};
</script>
