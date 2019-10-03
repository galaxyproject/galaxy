<template>
    <div>
        <b-alert :show="messageVisible" :variant="messageVariant"> {{ messageText }} </b-alert>
        <div v-if="itemsVisible" class="card-header">
            There are {{ itemsLength }}
            <b-button
                    size="sm"
                    @click.prevent="executeAll()"
                    :title=iconTooltipAll
                    data-placement="bottom"
                >
                    <span :class=iconClass />
            </b-button>
            {{ itemsPlural }} available.
        </div>
        <b-table
            id="items-grid"
            v-if="itemsVisible"
            striped
            :fields="itemsAttributes"
            :items="items"
        >
            <template v-slot:cell(execute)="data">
                <b-button
                    size="sm"
                    :title=iconTooltip
                    data-placement="bottom"
                    @click.prevent="execute([data.item.id])"
                >
                    <span :class=iconClass />
                </b-button>
            </template>
            <template v-slot:cell(links)="data">
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
            items: [],
            iconClass: "fa fa-refresh",
            iconTooltip: "Refresh",
            itemsPlural: "display applications",
            itemsLoaded: false,
            itemsSuccess: "reloaded",
            itemsAttributes: [
                { key: "execute", label: "Refresh" },
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
        iconTooltipAll: function() {
            return `${this.iconTooltip} all`
        },
        itemsIndex: function() {
            return this.items.reduce((r, v) => {
                r[v.id] = v;
                return r;
            }, {});
        },
        itemsAll: function() {
            return this.items.map(v => v.id);
        },
        itemsVisible: function() {
            return this.items.length > 0;
        },
        itemsLength: function() {
            return this.items.length;
        },
        messageVisible: function() {
            return this.messageText != null;
        }
    },
    created() {
        this.messageText = null;
        getDisplayApplications()
            .then(response => {
                this.items = response.data;
                this.itemsLoaded = true;
                if (!this.itemsVisible) {
                    this.messageVariant = "warning";
                    this.messageText = `No ${this.itemsPlural} available.`;
                }
            })
            .catch(e => {
                this._errorMessage(e);
            });
    },
    methods: {
        executeAll: function() {
            this.execute(this.itemsAll);
        },
        execute: function(ids) {
            this.messageVariant = "warning";
            this.messageText = "Executing request. Please wait...";
            this._highlightRows(this.itemsAll, "default");
            reloadDisplayApplications(ids)
                .then(response => {
                    const data = response.data;
                    if (data) {
                        this.messageVariant = "info";
                        this.messageText = data.message;
                        this._highlightRows(data.failed, "danger");
                        this._highlightRows(data[this.itemsSuccess], "success");
                    }
                })
                .catch(e => {
                    this._errorMessage(e);
                });
        },
        _highlightRows: function(ids, status) {
            if (ids) {
                for (const id of ids) {
                    const item = this.itemsIndex[id];
                    if (item) {
                        item._rowVariant = status;
                    }
                }
            }
        },
        _errorMessage: function(e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            this.messageText = message || "Request failed for an unknown reason.";
            this.messageVariant = "danger";
        }
    }
};
</script>