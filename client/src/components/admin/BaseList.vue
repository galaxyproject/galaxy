<template>
    <div>
        <b-alert :show="messageVisible" :variant="messageVariant"> {{ messageText }} </b-alert>
        <div v-if="itemsVisible" class="card-header">
            There are {{ itemsLength }}
            <b-button
                size="sm"
                :disabled="busy"
                :title="tooltipAll"
                data-placement="bottom"
                @click.prevent="executeAll()">
                <span :class="icon" />
            </b-button>
            {{ plural }} available.
        </div>
        <b-table v-if="itemsVisible" striped :fields="fields" :items="items">
            <template v-slot:cell(execute)="data">
                <b-button
                    size="sm"
                    :disabled="busy"
                    :title="tooltip"
                    data-placement="bottom"
                    @click.prevent="execute([data.item.id])">
                    <span :class="icon" />
                </b-button>
            </template>
            <template v-slot:cell(links)="data">
                <li v-for="link in data.item.links" :key="link.name">
                    {{ link.name }}
                </li>
            </template>
        </b-table>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        icon: {
            type: String,
        },
        tooltip: {
            type: String,
        },
        plural: {
            type: String,
        },
        success: {
            type: String,
        },
        fields: {
            type: Array,
        },
        getter: {
            type: Function,
        },
        setter: {
            type: Function,
        },
    },
    data() {
        return {
            items: [],
            busy: false,
            messageText: null,
            messageVariant: null,
        };
    },
    computed: {
        tooltipAll: function () {
            return `${this.tooltip} all`;
        },
        itemsIndex: function () {
            return this.items.reduce((r, v) => {
                r[v.id] = v;
                return r;
            }, {});
        },
        itemsAll: function () {
            return this.items.map((v) => v.id);
        },
        itemsVisible: function () {
            return this.items.length > 0;
        },
        itemsLength: function () {
            return this.items.length;
        },
        messageVisible: function () {
            return this.messageText != null;
        },
    },
    created() {
        this.messageText = null;
        this.getter()
            .then((response) => {
                this.items = response.data;
                if (!this.itemsVisible) {
                    this.messageVariant = "warning";
                    this.messageText = `No ${this.plural} available.`;
                }
            })
            .catch((e) => {
                this._errorMessage(e);
            });
    },
    methods: {
        executeAll: function () {
            this.execute(this.itemsAll);
        },
        execute: function (ids) {
            this.busy = true;
            this.messageVariant = "warning";
            this.messageText = "Executing request. Please wait...";
            this._highlightRows(this.itemsAll, "default");
            this.setter(ids)
                .then((response) => {
                    const data = response.data;
                    if (data) {
                        this.messageVariant = "info";
                        this.messageText = data.message;
                        this._highlightRows(data.failed, "danger");
                        this._highlightRows(data[this.success], "success");
                    }
                    this.busy = false;
                })
                .catch((e) => {
                    this._errorMessage(e);
                    this.busy = false;
                });
        },
        _highlightRows: function (ids, status) {
            if (ids) {
                for (const id of ids) {
                    const item = this.itemsIndex[id];
                    if (item) {
                        item._rowVariant = status;
                    }
                }
            }
        },
        _errorMessage: function (e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            this.messageText = message || "Request failed for an unknown reason.";
            this.messageVariant = "danger";
        },
    },
};
</script>
