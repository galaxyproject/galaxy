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
            <PermissionsInputField :folder_id="folder_id" :type="manage_type" :value="manage_ids" @input="setUserPermissionsPreferences"/>

            <div class="alert alert-info roles-selection">
                User with <strong>any</strong> of these roles can manage permissions on this folder.
            </div>
            <h4>
                Roles that can add items to this folder
            </h4>
            <PermissionsInputField :folder_id="folder_id" :type="add_type" :value="add_ids" @input="setUserPermissionsPreferences" />
            <div class="alert alert-info roles-selection">
                User with <strong>any</strong> of these roles can add items to this folder (folders and datasets).
            </div>
            <h4>
                Roles that can modify this folder
            </h4>
            <PermissionsInputField :folder_id="folder_id" :type="modify_type" :value="modify_ids" @input="setUserPermissionsPreferences" />
            <div class="alert alert-info roles-selection">
                User with <strong>any</strong> of these roles can modify this folder (name, etc.).
            </div>
            <button
                data-toggle="tooltip"
                data-placement="top"
                title="Save modifications"
                class="btn btn-secondary toolbtn_save_permissions primary-button"
                type="button"
                @click="postPermissions"
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
import PermissionsInputField from "./PermissionsInputField.vue";

import "vue-multiselect/dist/vue-multiselect.min.css";
import VueObserveVisibility from "vue-observe-visibility";

Vue.use(VueObserveVisibility);
Vue.use(BootstrapVue);

export default {
    props: {
        folder_id: {
            type: String,
            required: true,
        },
    },
    components: {
        PermissionsInputField,
    },
    data() {
        return {
            permissions: undefined,
            folder: undefined,
            is_admin: undefined,
            value: null,
            add_ids: [],
            modify_ids: [],
            manage_ids: [],
            add_type: "add_type",
            manage_type: "manage_type",
            modify_type: "modify_type",
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.is_admin = Galaxy.user.attributes.is_admin;

        this.services.getFolderPermissions(this.folder_id).then((response) => {
            this.permissions = response;
        });
        this.services.getFolder(this.folder_id).then((response) => {
            this.folder = response;
        });
    },

    methods: {
        getParentLink() {
            return `${this.root}library/folders/${this.folder.parent_id}`;
        },
        setUserPermissionsPreferences(ids, type) {
            switch (type) {
                case "manage":
                    this.manage_ids = ids;
                    break;
                case "add":
                    this.add_ids = ids;
                    break;
                case "modify":
                    this.modify_ids = ids;
                    break;
            }
        },
        postPermissions() {
            this.services.setPermissions(
                this.add_ids,
                this.manage_ids,
                this.modify_ids,
                (fetched_permissions) => {
                    Toast.success("Permissions saved.");
                    this.permissions = fetched_permissions;
                },
                (error) => {
                    Toast.error("An error occurred while attempting to set folder permissions.");
                    console.error(error);
                }
            );
        },
    },
};
</script>
