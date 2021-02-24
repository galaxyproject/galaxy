<template>
    <div>
        <div v-if="librariesList.length > 0"></div>
        <b-table
            id="libraries_list"
            striped
            hover
            :fields="fields"
            :items="librariesList"
            :per-page="perPage"
            :current-page="currentPage"
            show-empty
            ref="libraries_list"
        >
            <template v-slot:cell(name)="row">
                <b-link v-if="!row.item.editMode" :to="{ path: `/folders/${row.item.root_folder_id}` }">{{
                    row.item.name
                }}</b-link>
                <textarea v-else class="form-control" :ref="`name-${row.item.id}`" :value="row.item.name" rows="3" />
            </template>
            <template v-slot:cell(description)="row">
                <LibraryEditField
                    @refreshTable="refreshTable"
                    class="description-field"
                    property="description"
                    :item="row.item"
                />
            </template>
            <template v-slot:cell(synopsis)="row">
                <LibraryEditField @refreshTable="refreshTable" property="synopsis" :item="row.item" />
            </template>
            <template v-slot:cell(is_unrestricted)="row">
                <font-awesome-icon
                    v-if="row.item.public && !row.item.deleted"
                    title="Unrestricted dataset"
                    icon="globe"
                />
            </template>
            <template v-slot:cell(buttons)="row">
                <b-button
                    v-if="row.item.can_user_modify"
                    size="sm"
                    class="lib-btn edit-btn"
                    :title="`Edit ${row.item.name}`"
                    @click="toggleEditMode(row.item)"
                >
                    <font-awesome-icon icon="pencil-alt" />
                    {{ row.item.editMode ? "Cancel" : "Edit" }}
                </b-button>
                <b-button
                    v-if="row.item.can_user_manage"
                    size="sm"
                    class="lib-btn permission_folder_btn"
                    :title="'Permissions of ' + row.item.name"
                    :href="`${root}library/list#library/${row.item.id}/permissions`"
                >
                    <font-awesome-icon icon="users" />
                    Manage
                </b-button>
            </template>
        </b-table>

        <b-container>
            <b-row class="justify-content-md-center">
                <b-col md="auto">
                    <b-pagination
                        v-model="currentPage"
                        :total-rows="rows"
                        :per-page="perPage"
                        aria-controls="libraries_list"
                    >
                    </b-pagination>
                </b-col>
                <b-col cols="1.5">
                    <table>
                        <tr>
                            <td class="m-0 p-0">
                                <b-form-input
                                    class="pagination-input-field"
                                    id="paginationPerPage"
                                    autocomplete="off"
                                    type="number"
                                    v-model="perPage"
                                />
                            </td>
                            <td class="text-muted ml-1 paginator-text">
                                <span class="pagination-total-pages-text">per page, {{ rows }} total</span>
                            </td>
                        </tr>
                    </table>
                </b-col>
            </b-row>
        </b-container>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import { fields } from "./table-fields";
// import { Toast } from "ui/toast";
import { initLibariesIcons } from "components/Libraries/icons";
import { MAX_DESCRIPTION_LENGTH, DEFAULT_PER_PAGE } from "components/Libraries/library-utils";
import LibraryEditField from "components/Libraries/LibraryEditField";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import linkify from "linkifyjs/html";

initLibariesIcons();

Vue.use(BootstrapVue);

export default {
    components: {
        FontAwesomeIcon,
        LibraryEditField,
    },
    computed: {
        rows() {
            return this.librariesList.length;
        },
    },
    data() {
        return {
            currentPage: 1,
            fields: fields,
            perPage: DEFAULT_PER_PAGE,
            librariesList: [],
            maxDescriptionLength: MAX_DESCRIPTION_LENGTH,
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getLibraries().then((result) => (this.librariesList = result));
        console.log("this.librariesList", this.librariesList);
    },
    methods: {
        toggleEditMode(item) {
            item.editMode = !item.editMode;
            this.$refs.libraries_list.refresh();
        },
        toggleDescriptionExpand(item) {
            item.isExpanded = !item.isExpanded;
            console.log("isExpanded");
            console.log(item.isExpanded);
            this.$emit("refreshTable");
        },
        refreshTable() {
            console.log("!!!!!!");
            console.log("refresh");
            console.log("!!!!!!");
            this.$refs.libraries_list.refresh();
        },
    },
};
</script>
