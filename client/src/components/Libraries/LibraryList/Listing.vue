<template>
    <section>
        <!-- search filters and operation buttons -->
        <b-navbar class="my-2 px-0">
            <b-navbar-nav>
                <b-nav-form>
                    <b-form-input v-model="filterText" :placeholder="'Search Libraries' | l" :trim="true" />
                    <b-form-checkbox v-if="user.isAdmin" v-model="showDeleted" class="mx-2">
                        <span v-localize>Show Deleted</span>
                    </b-form-checkbox>
                    <b-form-checkbox v-model="excludeRestricted" class="mx-2">
                        <span v-localize>Hide Restricted</span>
                    </b-form-checkbox>
                </b-nav-form>
            </b-navbar-nav>

            <b-navbar-nav class="ml-auto">
                <b-button @click="createLibrary">
                    <span v-localize>Create Library</span>
                </b-button>
            </b-navbar-nav>
        </b-navbar>

        <!-- filtered & paginated listing -->
        <b-table
            class="my-2"
            v-if="libraries.length"
            striped
            hover
            :items="libraries"
            :fields="libraryFields"
            :current-page.sync="currentPage"
            :per-page="rowsPerPage"
            @row-clicked="selectLibrary"
            primary-key="id"
        >
            <template v-slot:cell(actions)="{ item }">
                <div>{{ item }}</div>
            </template>
            <template v-slot:table-caption>
                <b-pagination
                    v-if="libraries.length > rowsPerPage"
                    v-model="currentPage"
                    :total-rows="libraries.length"
                    :per-page="rowsPerPage"
                    align="center"
                />
            </template>
        </b-table>
        <div v-else>
            <span v-localize>No Results</span>
        </div>
    </section>
</template>

<script>
import { LibraryParams } from "../model";
import { debounce } from "lodash";
import User from "store/userStore/User";

export default {
    inject: ["log"],
    props: {
        user: { type: User, required: true },
        filters: { type: LibraryParams, required: true },
        libraries: { type: Array, default: () => [] },
        debouncePeriod: { type: Number, required: false, default: 250 },
        rowsPerPage: { type: Number, required: false, default: 10 },
    },
    data() {
        return {
            currentPage: 1,
        };
    },
    computed: {
        filterText: {
            get() {
                return this.filters.filterText;
            },
            set(filterText) {
                this.debouncedUpdateParams({ filterText });
            },
        },
        showDeleted: {
            get() {
                return this.filters.showDeleted;
            },
            set(showDeleted) {
                // debounce this because this results in a query
                this.debouncedUpdateParams({ showDeleted });
            },
        },
        excludeRestricted: {
            get() {
                return !this.filters.showRestricted;
            },
            set(excludeRestricted) {
                const showRestricted = !excludeRestricted;
                this.debouncedUpdateParams({ showRestricted });
            },
        },
        libraryFields() {
            return [{ key: "name", sortable: true }, { key: "description" }, { key: "synopsis" }, { key: "actions" }];
        },
    },
    created() {
        this.debouncedUpdateParams = debounce(this.updateParams, this.debouncePeriod);
    },
    methods: {
        updateParams(props) {
            this.$emit("update:filters", this.filters.clone(props));
        },
        createLibrary() {
            this.log("createLibrary");
        },
        selectLibrary(library) {
            this.$router.push({
                name: "Library",
                params: {
                    libraryId: library.id,
                },
            });
        },
    },
};
</script>

<!---
<style scoped>
.deleted-item {
    cursor: not-allowed;
    color: gray;
}
</style>

<div class="form-inline d-flex align-items-center mb-2">
    <b-button class="mr-1" @click="gotoFirstPage" title="go to first page">
        <font-awesome-icon icon="home" />
    </b-button>
    <b-button
        id="create-new-lib"
        v-b-toggle.collapse-2
        v-if="user.isAdmin"
        title="Create new folder"
        class="mr-1"
    >
        <font-awesome-icon icon="plus" />
        Library
    </b-button>
    <SearchField :typing-delay="0" @updateSearch="searchValue($event)" />
    <b-form-checkbox class="mr-1" @input="toggle_include_deleted($event)"> include deleted </b-form-checkbox>
    <b-form-checkbox class="mr-1" @input="toggle_exclude_restricted($event)">
        exclude restricted
    </b-form-checkbox>
</div>

<b-collapse v-model="isNewLibFormVisible" id="collapse-2">
    <b-card>
        <b-form @submit.prevent="newLibrary">
            <b-input-group class="mb-2 new-row">
                <b-form-input v-model="newLibraryForm.name" required placeholder="Name" />
                <b-form-input v-model="newLibraryForm.description" required placeholder="Description" />
                <b-form-input v-model="newLibraryForm.synopsis" placeholder="Synopsis" />
                <template v-slot:append>
                    <b-button id="save_new_library" type="submit" title="save">
                        <font-awesome-icon :icon="['far', 'save']" />
                        Save
                    </b-button>
                </template>
            </b-input-group>
        </b-form>
    </b-card>
</b-collapse>

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
    :filter-included-fields="filterOn"
>
    <template v-slot:cell(name)="row">
        <textarea
            v-if="row.item.editMode"
            class="form-control input_library_name"
            :ref="`name-${row.item.id}`"
            :value="row.item.name"
            rows="3"
        />

        <div class="deleted-item" v-else-if="row.item.deleted && include_deleted">{{ row.item.name }}</div>
        <b-link v-else :to="{ path: `folders/${row.item.root_folder_id}` }">{{ row.item.name }}</b-link>
    </template>
    <template v-slot:cell(description)="row">
        <LibraryEditField
            @toggleDescriptionExpand="toggleDescriptionExpand(row.item)"
            :ref="`description-${row.item.id}`"
            :is-expanded="row.item.isExpanded"
            :is-edit-mode="row.item.editMode"
            :text="row.item.description"
        />
    </template>
    <template v-slot:cell(synopsis)="row">
        <LibraryEditField
            @toggleDescriptionExpand="toggleDescriptionExpand(row.item)"
            :ref="`synopsis-${row.item.id}`"
            :is-expanded="row.item.isExpanded"
            :is-edit-mode="row.item.editMode"
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
                class="lib-btn edit_library_btn save_library_btn"
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
                class="lib-btn permission_library_btn"
                :title="'Permissions of ' + row.item.name"
                :to="{ path: `/${row.item.id}/permissions` }"
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

--->