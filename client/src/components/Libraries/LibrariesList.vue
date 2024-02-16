<template>
    <div>
        <div class="form-inline d-flex align-items-center mb-2">
            <b-button class="mr-1" title="go to first page" @click="gotoFirstPage">
                <FontAwesomeIcon icon="home" />
            </b-button>
            <b-button
                v-if="currentUser && currentUser.is_admin"
                id="create-new-lib"
                v-b-toggle.collapse-2
                title="Create new folder"
                class="mr-1">
                <FontAwesomeIcon icon="plus" />
                {{ titleLibrary }}
            </b-button>
            <SearchField :typing-delay="0" @updateSearch="searchValue($event)" />
            <b-form-checkbox
                v-if="currentUser && currentUser.is_admin"
                v-localize
                class="mr-1"
                @input="toggle_include_deleted($event)">
                include deleted
            </b-form-checkbox>
            <b-form-checkbox v-localize class="mr-1" @input="toggle_exclude_restricted($event)">
                exclude restricted
            </b-form-checkbox>
        </div>
        <b-collapse id="collapse-2" v-model="isNewLibFormVisible">
            <b-card>
                <b-form @submit.prevent="newLibrary">
                    <b-input-group class="mb-2 new-row">
                        <b-form-input v-model="newLibraryForm.name" required :placeholder="titleName" />
                        <b-form-input v-model="newLibraryForm.description" required :placeholder="titleDescription" />
                        <b-form-input v-model="newLibraryForm.synopsis" :placeholder="titleSynopsis" />
                        <template v-slot:append>
                            <b-button id="save_new_library" type="submit" :title="titleSave">
                                <FontAwesomeIcon :icon="['far', 'save']" />
                                {{ titleSave }}
                            </b-button>
                        </template>
                    </b-input-group>
                </b-form>
            </b-card>
        </b-collapse>
        <b-table
            id="libraries_list"
            ref="libraries_list"
            no-sort-reset
            striped
            hover
            :fields="fields"
            :items="librariesList"
            :sort-by.sync="sortBy"
            :per-page="perPage"
            :current-page="currentPage"
            show-empty
            :filter="filter"
            :filter-included-fields="filterOn"
            @filtered="onFiltered">
            <template v-slot:cell(name)="row">
                <textarea
                    v-if="row.item.editMode"
                    v-model="row.item.name"
                    aria-label="Library name"
                    class="form-control input_library_name"
                    rows="3" />

                <div v-else-if="row.item.deleted && includeDeleted" class="deleted-item">{{ row.item.name }}</div>
                <b-link v-else :to="{ path: `/libraries/folders/${row.item.root_folder_id}` }">
                    {{ row.item.name }}
                </b-link>
            </template>
            <template v-slot:cell(description)="{ item }">
                <LibraryEditField
                    :ref="`description-${item.id}`"
                    :is-expanded="item.isExpanded"
                    :is-edit-mode="item.editMode"
                    :text="item.description"
                    :changed-value.sync="item[newDescriptionProperty]"
                    @toggleDescriptionExpand="toggleDescriptionExpand(item)" />
            </template>
            <template v-slot:cell(synopsis)="{ item }">
                <LibraryEditField
                    :ref="`synopsis-${item.id}`"
                    :is-expanded="item.isExpanded"
                    :is-edit-mode="item.editMode"
                    :text="item.synopsis"
                    :changed-value.sync="item[newSynopsisProperty]"
                    @toggleDescriptionExpand="toggleDescriptionExpand(item)" />
            </template>
            <template v-slot:cell(is_unrestricted)="row">
                <FontAwesomeIcon v-if="row.item.public && !row.item.deleted" title="Public library" icon="globe" />
            </template>
            <template v-slot:cell(buttons)="row">
                <b-button
                    v-if="row.item.deleted"
                    size="sm"
                    :title="'Undelete ' + row.item.name"
                    @click="undelete(row.item)">
                    <FontAwesomeIcon icon="unlock" />
                    {{ titleUndelete }}
                </b-button>
                <b-button
                    v-if="row.item.can_user_modify && row.item.editMode"
                    size="sm"
                    class="lib-btn permission_folder_btn"
                    :title="'Permissions of ' + row.item.name"
                    @click="saveChanges(row.item)">
                    <FontAwesomeIcon :icon="['far', 'save']" />
                    {{ titleSave }}
                </b-button>
                <b-button
                    v-if="row.item.can_user_modify && !row.item.deleted"
                    size="sm"
                    class="lib-btn edit_library_btn save_library_btn"
                    :title="`Edit ${row.item.name}`"
                    @click="toggleEditMode(row.item)">
                    <div v-if="!row.item.editMode">
                        <FontAwesomeIcon icon="pencil-alt" />
                        {{ titleEdit }}
                    </div>
                    <div v-else>
                        <FontAwesomeIcon :icon="['fas', 'times']" />
                        {{ titleCancel }}
                    </div>
                </b-button>
                <b-button
                    v-if="currentUser && currentUser.is_admin && !row.item.deleted"
                    size="sm"
                    class="lib-btn permission_library_btn"
                    :title="'Permissions of ' + row.item.name"
                    :to="{ path: `/libraries/${row.item.id}/permissions` }">
                    <FontAwesomeIcon icon="users" />
                    Manage
                </b-button>
                <b-button
                    v-if="currentUser && currentUser.is_admin && row.item.editMode && !row.item.deleted"
                    size="sm"
                    class="lib-btn delete-lib-btn"
                    :title="`Delete ${row.item.name}`"
                    @click="deleteLibrary(row.item)">
                    <FontAwesomeIcon icon="trash" />
                    {{ titleDelete }}
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
                        aria-controls="libraries_list">
                    </b-pagination>
                </b-col>
                <b-col cols="1.5">
                    <table>
                        <tr>
                            <td class="m-0 p-0">
                                <b-form-input
                                    id="paginationPerPage"
                                    v-model="perPage"
                                    class="pagination-input-field"
                                    autocomplete="off"
                                    type="number"
                                    onkeyup="this.value|=0;if(this.value<1)this.value=1" />
                            </td>
                            <td class="text-muted ml-1 paginator-text">
                                <span class="pagination-total-pages-text"
                                    >{{ titlePerPage }}, {{ rows }} {{ titleTotal }}</span
                                >
                            </td>
                        </tr>
                    </table>
                </b-col>
            </b-row>
        </b-container>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import { initLibrariesIcons } from "components/Libraries/icons";
import { DEFAULT_PER_PAGE, MAX_DESCRIPTION_LENGTH, onError } from "components/Libraries/library-utils";
import LibraryEditField from "components/Libraries/LibraryEditField";
import SearchField from "components/Libraries/LibraryFolder/SearchField";
import { Toast } from "composables/toast";
import { getAppRoot } from "onload/loadConfig";
import { mapState } from "pinia";
import _l from "utils/localization";
import Vue from "vue";

import { useUserStore } from "@/stores/userStore";

import { Services } from "./services";
import { fields } from "./table-fields";

initLibrariesIcons();

Vue.use(BootstrapVue);

export default {
    components: {
        FontAwesomeIcon,
        LibraryEditField,
        SearchField,
    },
    data() {
        return {
            newDescriptionProperty: "newDescription",
            newSynopsisProperty: "newSynopsis",
            isNewLibFormVisible: false,
            currentPage: 1,
            fields: fields,
            perPage: DEFAULT_PER_PAGE,
            librariesList: [],
            maxDescriptionLength: MAX_DESCRIPTION_LENGTH,
            includeDeleted: false,
            exclude_restricted: false,
            filterOn: [],
            excluded: [],
            filter: null,
            newLibraryForm: {
                name: "",
                description: "",
                synopsis: "",
            },
            titleLibrary: _l("Library"),
            titleName: _l("Name"),
            titleDescription: _l("Description"),
            titleSynopsis: _l("Synopsis"),
            titleSave: _l("Save"),
            titleUndelete: _l("Undelete"),
            titleEdit: _l("Edit"),
            titleCancel: _l("Cancel"),
            titleDelete: _l("Delete"),
            titlePerPage: _l("per page"),
            titleTotal: _l("total"),
            sortBy: "name",
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        rows() {
            return this.librariesList.length;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.loadLibraries(this.includeDeleted);
    },
    methods: {
        loadLibraries(includeDeleted = false) {
            this.services.getLibraries(includeDeleted).then((result) => (this.librariesList = result));
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
            const description = item[this.newDescriptionProperty];
            const synopsis = item[this.newSynopsisProperty];
            if (description) {
                item.description = description;
            }
            if (synopsis) {
                item.synopsis = synopsis;
            }
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
                    deletedLib.deleted = true;
                    this.toggleEditMode(deletedLib);
                    if (!this.includeDeleted) {
                        this.hideOn("deleted", false);
                    }
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
            this.includeDeleted = isDeletedIncluded;
            if (this.includeDeleted) {
                this.services.getLibraries(this.includeDeleted).then((result) => {
                    this.librariesList = this.librariesList.concat(result);
                    this.$refs.libraries_list.refresh();
                });
            } else {
                this.hideOn("deleted", false);
            }
        },
        toggle_exclude_restricted(isRestrictedIncluded) {
            this.exclude_restricted = isRestrictedIncluded;
            if (this.exclude_restricted) {
                this.excluded = this.hideOn("public", true);
            } else {
                this.librariesList = this.librariesList.concat(this.excluded);
            }
        },
        hideOn(property, value) {
            const filtered = [];
            this.librariesList = this.librariesList.filter((lib) => {
                if (lib[property] === value) {
                    return lib;
                } else {
                    filtered.push(lib);
                }
            });
            return filtered;
        },
        undelete(item) {
            this.services.deleteLibrary(
                item,
                () => {
                    item.deleted = false;
                    Toast.success("Library has been undeleted.");
                    this.$refs.libraries_list.refresh();
                },
                (error) => onError(error),
                true
            );
        },
        newLibrary() {
            this.services.createNewLibrary(
                this.newLibraryForm.name,
                this.newLibraryForm.description,
                this.newLibraryForm.synopsis,
                (newLib) => {
                    this.librariesList.push(newLib);
                    this.newLibraryForm.name = "";
                    this.newLibraryForm.description = "";
                    this.newLibraryForm.synopsis = "";
                    this.isNewLibFormVisible = false;
                    Toast.success("Library created.");
                },
                (error) => onError(error)
            );
        },
    },
};
</script>
<style scoped>
.deleted-item {
    cursor: not-allowed;
    color: gray;
}
</style>
