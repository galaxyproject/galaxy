<template>
    <div>
        <b-table
            small
            hover
            :items="items"
            :fields="fields"
            :filter="filter"
            :per-page="perPage"
            :current-page="currentPage"
            @row-clicked="clicked"
            @filtered="filtered"
        >
            <template v-slot:cell(label)="data">
                <pre
                    v-if="isEncoded"
                    :title="data.item.labelTitle"
                ><code>{{ data.value ? data.value : "-" }}</code></pre>
                <span v-else>
                    <i v-if="data.item.isLeaf" :class="leafIcon" /> <i v-else class="fa fa-folder" />
                    <span :title="data.item.labelTitle">{{ data.value ? data.value : "-" }}</span>
                </span>
            </template>
            <template v-slot:cell(details)="data">
                {{ data.value ? data.value : "-" }}
            </template>
            <template v-slot:cell(time)="data">
                {{ data.value ? data.value : "-" }}
            </template>
            <template v-slot:cell(navigate)="data">
                <i v-if="!data.item.isLeaf" class="fa fa-caret-square-o-right" @click.stop="open(data.item)" />
            </template>
        </b-table>
        <div v-if="nItems === 0">
            <div v-if="filter">
                No search results found for: <b>{{ this.filter }}</b
                >.
            </div>
            <div v-else>No entries.</div>
        </div>
        <b-pagination v-if="nItems > perPage" v-model="currentPage" :per-page="perPage" :total-rows="nItems" />
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

const LABEL_FIELD = { key: "label", sortable: true };
const DETAILS_FIELD = { key: "details", sortable: true };
const TIME_FIELD = { key: "time", sortable: true };
const NAVIGATE_FIELD = { key: "navigate", label: "", sortable: false };

export default {
    props: {
        items: {
            type: Array,
            required: true,
        },
        filter: {
            type: String,
            default: null,
        },
        multiple: {
            type: Boolean,
            default: false,
        },
        leafIcon: {
            type: String,
            default: "fa fa-file-o",
        },
        showDetails: {
            type: Boolean,
            default: true,
        },
        showTime: {
            type: Boolean,
            default: true,
        },
        showNavigate: {
            type: Boolean,
            default: false,
        },
        isEncoded: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            currentPage: 1,
            nItems: 0,
            perPage: 100,
        };
    },
    watch: {
        items: {
            immediate: true,
            handler(items) {
                this.filtered(items);
            },
        },
    },
    computed: {
        fields: function () {
            const fields = [LABEL_FIELD];
            if (this.showDetails) {
                fields.push(DETAILS_FIELD);
            }
            if (this.showTime) {
                fields.push(TIME_FIELD);
            }
            if (this.showNavigate) {
                fields.push(NAVIGATE_FIELD);
            }
            return fields;
        },
    },
    methods: {
        /** Resets pagination when a filter/search word is entered **/
        filtered: function (items) {
            this.nItems = items.length;
            this.currentPage = 1;
        },
        /** Collects selected datasets in value array **/
        clicked: function (record) {
            this.$emit("clicked", record);
        },
        open: function (record) {
            this.$emit("open", record);
        },
    },
};
</script>
