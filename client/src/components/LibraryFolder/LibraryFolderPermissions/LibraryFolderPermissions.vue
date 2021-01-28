<template>
    <div>
        <div>
            <a :href="getParentLink">
                <button
                    data-toggle="tooltip"
                    data-placement="top"
                    title="Go back to the parent folder"
                    class="btn btn-secondary primary-button"
                    type="button"
                >
                    <span class="fa fa-caret-left fa-lg" />
                    &nbsp;Parent folder
                </button>
            </a>
        </div>

        <h1>Folder: {{ folder.name }}</h1>

        <div class="alert alert-warning">
            <div v-if="is_admin">
                You are logged in as an <strong>administrator</strong> therefore you can manage any folder on this
                Galaxy instance. Please make sure you understand the consequences.
            </div>
            <div v-else>
                You can assign any number of roles to any of the following permission types. However please read
                carefully the implications of such actions.
            </div>
        </div>

        <div class="dataset_table">
            <h2>Folder permissions</h2>
            <h4>
                Roles that can manage permissions on this folder
            </h4>

            <multiselect
                v-if="options.roles.length > 0"
                v-model="value"
                :options="options.roles"
                :clear-on-select="true"
                :preserve-search="true"
                :multiple="true"
                label="name"
                track-by="id"
            >
            </multiselect>

            <div class="alert alert-info roles-selection">
                User with <strong>any</strong> of these roles can manage permissions on this folder.
            </div>
            <h4>
                Roles that can add items to this folder
            </h4>
            <div id="add_perm" class="add_perm roles-selection"></div>
            <div class="alert alert-info roles-selection">
                User with <strong>any</strong> of these roles can add items to this folder (folders and datasets).
            </div>
            <h4>
                Roles that can modify this folder
            </h4>
            <div id="modify_perm" class="modify_perm roles-selection"></div>
            <div class="alert alert-info roles-selection">
                User with <strong>any</strong> of these roles can modify this folder (name, etc.).
            </div>
            <button
                data-toggle="tooltip"
                data-placement="top"
                title="Save modifications"
                class="btn btn-secondary toolbtn_save_permissions primary-button"
                type="button"
            >
                <span class="fa fa-floppy-o" />
                &nbsp;Save
            </button>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import Utils from "utils/utils";
import { Toast } from "ui/toast";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import Multiselect from "vue-multiselect";
import "vue-multiselect/dist/vue-multiselect.min.css";

Vue.use(BootstrapVue);

export default {
    props: {
        folder_id: {
            type: String,
            required: true,
        },
    },
    components: {
        Multiselect,
    },
    data() {
        return {
            permissisons: undefined,
            folder: undefined,
            is_admin: undefined,
            options: { roles: [] },
            value: null,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.is_admin = Galaxy.user.attributes.is_admin;

        this.services.getFolderPermissions(this.folder_id).then((response) => {
            this.permissisons = response;
        });
        this.services.getFolder(this.folder_id).then((response) => {
            this.folder = response;
        });
        this.getSelectOptions();
    },
    methods: {
        getSelectOptions() {
            this.services.getSelectOptions(this.folder_id, true, 1).then((response) => {
                console.log(response)
                if (this.options.page > 1) {
                    this.options.roles.concat(response.roles);
                } else {
                    this.options = response;
                }
            });
        },
        getParentLink() {
            return `${this.root}library/folders/${this.folder.parent_id}`;
        },
    },
};
</script>
