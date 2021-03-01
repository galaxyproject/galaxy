<template>
    <div>
        <div class="form-inline d-flex align-items-center mb-2">
            <b-button @click="gotoFirstPage" title="go to first page">
                <font-awesome-icon icon="home" />
            </b-button>
            <SearchField :typingDelay="0" @updateSearch="searchValue($event)" />
            <b-form-checkbox @input="toggle_include_deleted($event)">
                include deleted
            </b-form-checkbox>
        </div>
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
            @filtered="onFiltered"
            :filter="filter"
            :filterIncludedFields="filterOn"
        >
            <template v-slot:cell(name)="row">
                <textarea
                    v-if="row.item.editMode"
                    class="form-control"
                    :ref="`name-${row.item.id}`"
                    :value="row.item.name"
                    rows="3"
                />

                <div class="deleted-item" v-else-if="row.item.deleted && include_deleted">{{ row.item.name }}</div>
                <b-link :disabled="true" v-else :to="{ path: `/folders/${row.item.root_folder_id}` }">{{
                    row.item.name
                }}</b-link>
            </template>
            <template v-slot:cell(description)="row">
                <LibraryEditField
                    @toggleDescriptionExpand="toggleDescriptionExpand(row.item)"
                    :ref="`description-${row.item.id}`"
                    :isExpanded="row.item.isExpanded"
                    :isEditMode="row.item.editMode"
                    :text="row.item.description"
                />
            </template>
            <template v-slot:cell(synopsis)="row">
                <LibraryEditField
                    @toggleDescriptionExpand="toggleDescriptionExpand(row.item)"
                    :ref="`synopsis-${row.item.id}`"
                    :isExpanded="row.item.isExpanded"
                    :isEditMode="row.item.editMode"
                    :text="row.item.synopsis"
                />
            </template>
            <template v-slot:cell(is_unrestricted)="row">
                <font-awesome-icon
                    v-if="row.item.public && !row.item.deleted"
                    title="Unrestricted dataset"
                    icon="globe"
                />
            </template>
            <template v-slot:cell(buttons)="row">
                <b-button @click="undelete(row.item)" v-if="row.item.deleted" :title="'Undelete ' + row.item.name">
                    <font-awesome-icon icon="unlock" />
                    Undelete
                </b-button>
                <div v-else>
                    <b-button
                        v-if="row.item.can_user_modify && row.item.editMode"
                        size="sm"
                        class="lib-btn permission_folder_btn"
                        :title="'Permissions of ' + row.item.name"
                        @click="saveChanges(row.item)"
                    >
                        <font-awesome-icon :icon="['far', 'save']" />
                        Save
                    </b-button>
                    <b-button
                        v-if="row.item.can_user_modify"
                        size="sm"
                        class="lib-btn edit-btn"
                        :title="`Edit ${row.item.name}`"
                        @click="toggleEditMode(row.item)"
                    >
                        <div v-if="!row.item.editMode">
                            <font-awesome-icon icon="pencil-alt" />
                            Edit
                        </div>
                        <div v-else>
                            <font-awesome-icon :icon="['fas', 'times']" />
                            Cancel
                        </div>
                    </b-button>
                    <b-button
                        v-if="row.item.can_user_manage && !row.item.editMode"
                        size="sm"
                        class="lib-btn permission_folder_btn"
                        :title="'Permissions of ' + row.item.name"
                        :href="`${root}library/list#library/${row.item.id}/permissions`"
                    >
                        <font-awesome-icon icon="users" />
                        Manage
                    </b-button>
                    <b-button
                        v-if="row.item.editMode"
                        size="sm"
                        class="lib-btn delete-lib-btn"
                        :title="`Delete ${row.item.name}`"
                        @click="deleteLibrary(row.item)"
                    >
                        <font-awesome-icon icon="trash" />
                        Delete
                    </b-button>
                </div>
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
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import { fields } from "./table-fields";
import { Toast } from "ui/toast";
import { initLibariesIcons } from "components/Libraries/icons";
import { MAX_DESCRIPTION_LENGTH, DEFAULT_PER_PAGE, onError } from "components/Libraries/library-utils";
import LibraryEditField from "components/Libraries/LibraryEditField";
import SearchField from "components/Libraries/LibraryFolder/SearchField";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

initLibariesIcons();

Vue.use(BootstrapVue);

export default {
    components: {
        FontAwesomeIcon,
        LibraryEditField,
        SearchField,
    },
    computed: {
        rows() {
            return this.librariesList.length;
        },
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            currentPage: 1,
            fields: fields,
            perPage: DEFAULT_PER_PAGE,
            librariesList: [],
            maxDescriptionLength: MAX_DESCRIPTION_LENGTH,
            include_deleted: false,
            filterOn: [],
            filter: null,
            isAdmin: galaxy.user.isAdmin(),
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.loadLibraries(this.include_deleted);
    },
    methods: {
        loadLibraries(include_deleted = false) {
            this.services.getLibraries(include_deleted).then((result) => (this.librariesList = result));
        },
        toggleEditMode(item) {
            item.editMode = !item.editMode;
            this.$refs.libraries_list.refresh();
        },
        toggleDescriptionExpand(item) {
            item.isExpanded = !item.isExpanded;
            this.$refs.libraries_list.refresh();
        },
        saveChanges(item) {
            item.description = this.$refs[`description-${item.id}`].textField;
            item.synopsis = this.$refs[`synopsis-${item.id}`].textField;
            this.services.saveChanges(
                item,
                () => {
                    Toast.success("Changes to library saved");
                },
                (error) => onError(error)
            );
            this.toggleEditMode(item);
        },
        deleteLibrary(deletedLib) {
            this.services.deleteLibrary(
                deletedLib,
                () => {
                    Toast.success("Library has been marked deleted.");
                    deletedLib.delete = true;
                    if (this.include_deleted)
                        this.librariesList = this.librariesList.filter((lib) => {
                            if (lib.id !== deletedLib.id) {
                                return lib;
                            }
                        });
                },
                (error) => onError(error)
            );
        },
        gotoFirstPage() {
            this.currentPage = 1;
        },
        onFiltered(filteredItems) {
            // Trigger pagination to update the number of buttons/pages due to filtering
            this.totalRows = filteredItems.length;
            this.currentPage = 1;
        },
        searchValue(value) {
            this.filter = value;
        },
        toggle_include_deleted(isDeletedIncluded) {
            this.include_deleted = isDeletedIncluded;
            if (this.include_deleted) {
                this.services.getLibraries(this.include_deleted).then((result) => {
                    this.librariesList = this.librariesList.concat(result);
                    this.$refs.libraries_list.refresh();
                });
            } else {
                this.hideOn("deleted", false);
            }
        },
        hideOn(property, value) {
            this.librariesList = this.librariesList.filter((lib) => {
                if (lib[property] === value) {
                    return lib;
                }
            });
        },
        undelete() {},
    },
};
</script>
<style scoped>
.deleted-item {
    cursor: not-allowed;
    color: gray;
}
</style>
