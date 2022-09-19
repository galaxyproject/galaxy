<template>
    <div>
        <!-- todo: rewrite this to send events up instead of two way prop binding -->
        <!-- eslint-disable vue/no-mutating-props-->
        <b-table
            small
            hover
            :items="items"
            :fields="fields"
            :filter="filter"
            :per-page="perPage"
            :current-page="currentPage"
            :busy.sync="isBusy"
            @row-clicked="clicked"
            @filtered="filtered">
            <template v-slot:head(select_icon)="">
                <font-awesome-icon
                    class="select-checkbox cursor-pointer"
                    title="Check to select all datasets"
                    :icon="selectionIcon(selectAllIcon)"
                    @click="$emit('toggleSelectAll')" />
            </template>
            <template v-slot:cell(select_icon)="data">
                <font-awesome-icon :icon="selectionIcon(data.item._rowVariant)" />
            </template>
            <template v-slot:cell(label)="data">
                <div style="cursor: pointer">
                    <pre
                        v-if="isEncoded"
                        :title="`label-${data.item.labelTitle}`"><code>{{ data.value ? data.value : "-" }}</code></pre>
                    <span v-else>
                        <div v-if="data.item.isLeaf">
                            <i :class="leafIcon" />
                            <span :title="`label-${data.item.labelTitle}`">{{ data.value ? data.value : "-" }}</span>
                        </div>
                        <div v-else @click.stop="open(data.item)">
                            <font-awesome-icon icon="folder" />
                            <b-link :title="`label-${data.item.labelTitle}`">{{
                                data.value ? data.value : "-"
                            }}</b-link>
                        </div>
                    </span>
                </div>
            </template>
            <template v-slot:cell(details)="data">
                <span :title="`details-${data.item.labelTitle}`">{{ data.value ? data.value : "-" }}</span>
            </template>
            <template v-slot:cell(time)="data">
                {{ data.value ? data.value : "-" }}
            </template>
        </b-table>
        <div v-if="isBusy" class="text-center">
            <b-spinner small type="grow"></b-spinner>
            <b-spinner small type="grow"></b-spinner>
            <b-spinner small type="grow"></b-spinner>
        </div>
        <div v-if="nItems === 0">
            <div v-if="filter">
                No search results found for: <b>{{ filter }}</b
                >.
            </div>
            <div v-else>No entries.</div>
        </div>
        <b-pagination
            v-if="nItems > perPage"
            v-model="currentPage"
            class="justify-content-md-center"
            :per-page="perPage"
            :total-rows="nItems" />
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { faCheckSquare, faSquare, faMinusSquare } from "@fortawesome/free-regular-svg-icons";
import { faFolder } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { selectionStates } from "components/SelectionDialog/selectionStates";

Vue.use(BootstrapVue);
library.add(faCheckSquare, faSquare, faFolder, faMinusSquare);

const LABEL_FIELD = { key: "label", sortable: true };
const DETAILS_FIELD = { key: "details", sortable: true };
const TIME_FIELD = { key: "time", sortable: true };
const SELECT_ICON_FIELD = { key: "select_icon", label: "", sortable: false };

export default {
    components: {
        FontAwesomeIcon,
    },
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
        selectAllIcon: {
            type: String,
            default: selectionStates.unselected,
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
        showSelectIcon: {
            type: Boolean,
            default: false,
        },
        isEncoded: {
            type: Boolean,
            default: false,
        },
        isBusy: {
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
    computed: {
        fields: function () {
            const fields = [];
            if (this.showSelectIcon) {
                fields.push(SELECT_ICON_FIELD);
            }
            fields.push(LABEL_FIELD);
            if (this.showDetails) {
                fields.push(DETAILS_FIELD);
            }
            if (this.showTime) {
                fields.push(TIME_FIELD);
            }

            return fields;
        },
    },
    watch: {
        items: {
            immediate: true,
            handler(items) {
                this.filtered(items);
            },
        },
    },
    methods: {
        selectionIcon(variant) {
            switch (variant) {
                case selectionStates.selected:
                    return ["far", "check-square"];
                case selectionStates.mixed:
                    return ["fas", "minus-square"];
                default:
                    return ["far", "square"];
            }
        },
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
