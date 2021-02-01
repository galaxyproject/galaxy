<template>
    <div>
        <div>
            <div v-if="folder">
                <b-button variant="primary" :href="getParentLink()">
                    <font-awesome-icon icon="angle-double-left">1</font-awesome-icon>
                </b-button>
                <div>
                    <div class="header text-center">{{ folder.name }}</div>
                </div>
            </div>
            <div>
                <div class="text-center">
                    <b-alert show variant="warning" v-if="is_admin">
                        You are logged in as an <strong>administrator</strong> therefore you can manage any folder on
                        this Galaxy instance. Please make sure you understand the consequences.
                    </b-alert>
                    <b-alert show variant="warning" v-else>
                        You can assign any number of roles to any of the following permission types. However please read
                        carefully the implications of such actions.
                    </b-alert>
                </div>
            </div>
            <hr class="my-4" />
            <b-card border-variant="white">
                <div class="dataset_table">
                    <h2>Folder permissions</h2>
                    <h4>
                        Roles that can manage permissions on this folder
                    </h4>
                    <b-row>
                        <b-col>
                            <PermissionsInputField
                                v-if="manage_folder_role_list"
                                :folder_id="folder_id"
                                :permission_type="manage_type"
                                :initial_value="manage_folder_role_list"
                                @input="setUserPermissionsPreferences"
                        /></b-col>
                        <b-col>
                            <b-alert show variant="info">
                                User with <strong>any</strong> of these roles can manage permissions on this folder.
                            </b-alert>
                        </b-col>
                    </b-row>
                    <h4>
                        Roles that can add items to this folder
                    </h4>
                    <b-row>
                        <b-col>
                            <PermissionsInputField
                                v-if="add_library_item_role_list"
                                :folder_id="folder_id"
                                :permission_type="add_type"
                                :initial_value="add_library_item_role_list"
                                @input="setUserPermissionsPreferences"
                        /></b-col>
                        <b-col>
                            <b-alert class="p-3" show variant="info">
                                User with <strong>any</strong> of these roles can add items to this folder (folders and
                                datasets).
                            </b-alert>
                        </b-col>
                    </b-row>
                    <h4>
                        Roles that can modify this folder
                    </h4>
                    <b-row>
                        <b-col>
                            <PermissionsInputField
                                v-if="modify_folder_role_list"
                                :folder_id="folder_id"
                                :permission_type="modify_type"
                                :initial_value="modify_folder_role_list"
                                @input="setUserPermissionsPreferences"
                        /></b-col>
                        <b-col>
                            <b-alert show variant="info">
                                User with <strong>any</strong> of these roles can modify this folder (name, etc.).
                            </b-alert></b-col
                        >
                    </b-row>
                    <button
                        data-toggle="tooltip"
                        data-placement="top"
                        title="Save modifications"
                        class="btn btn-secondary toolbtn_save_permissions primary-button"
                        type="button"
                        @click="postPermissions"
                    >
                        <font-awesome-icon :icon="['far', 'save']" />
                        &nbsp;Save
                    </button>
                </div>
            </b-card>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import { Toast } from "ui/toast";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import PermissionsInputField from "./PermissionsInputField.vue";
import { initManageFolderIcons } from "components/LibraryFolder/icons";

import "vue-multiselect/dist/vue-multiselect.min.css";
import VueObserveVisibility from "vue-observe-visibility";

Vue.use(VueObserveVisibility);
Vue.use(BootstrapVue);
initManageFolderIcons();

export default {
    props: {
        folder_id: {
            type: String,
            required: true,
        },
    },
    components: {
        PermissionsInputField,
        FontAwesomeIcon,
    },
    data() {
        return {
            permissions: undefined,
            folder: undefined,
            is_admin: undefined,
            add_library_item_role_list: undefined,
            modify_folder_role_list: undefined,
            manage_folder_role_list: undefined,
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
        this.services.getFolderPermissions(this.folder_id).then((fetched_permissions) => {
            this.add_library_item_role_list = this._serializeRoles(fetched_permissions.add_library_item_role_list);
            this.manage_folder_role_list = this._serializeRoles(fetched_permissions.manage_folder_role_list);
            this.modify_folder_role_list = this._serializeRoles(fetched_permissions.modify_folder_role_list);
        });
        this.services.getFolder(this.folder_id).then((response) => {
            this.folder = response;
        });
    },

    methods: {
        getParentLink() {
            return `${this.root}library/folders/${this.folder.parent_id}`;
        },
        setUserPermissionsPreferences(ids, permission_type) {
            switch (permission_type) {
                case "manage_type":
                    this.manage_folder_role_list = ids;
                    break;
                case "add_type":
                    this.add_library_item_role_list = ids;
                    break;
                case "modify_type":
                    this.modify_folder_role_list = ids;
                    break;
            }
        },
        postPermissions() {
            this.services.setPermissions(
                this.folder_id,
                this.add_library_item_role_list,
                this.manage_folder_role_list,
                this.modify_folder_role_list,
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

        _serializeRoles: function (role_list) {
            const selected_roles = [];
            role_list.forEach((item) => {
                selected_roles.push({ name: item[0], id: item[1] });
            });

            return selected_roles;
        },
    },
};
</script>

<style scoped>
.header {
    font-size: 45px;
}
</style>
