<template>
    <div>
        <div v-if="librariesList.length > 0"></div>
        <b-table id="list_body" striped hover :fields="fields" :items="librariesList" ref="libraries-list" show-empty>
            <template v-slot:cell(name)="row">
                <b-link :to="{ path: `/folders/${row.item.root_folder_id}` }">{{ row.item.name }}</b-link>
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
                    v-if="row.item.can_manage && !row.item.deleted"
                    :href="`library/list#library/${row.root_folder_id}/permissions`"
                    data-toggle="tooltip"
                    data-placement="top"
                    size="sm"
                    class="lib-btn permission_folder_btn"
                    :title="'Permissions of ' + row.item.name"
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
                        aria-controls="libraries-list"
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
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

initLibariesIcons();

Vue.use(BootstrapVue);

export default {
    components: {
        FontAwesomeIcon,
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
            perPage: 10,
            librariesList: [],
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getLibraries().then((result) => (this.librariesList = result));
        console.log("this.librariesList", this.librariesList);
    },
};
</script>
