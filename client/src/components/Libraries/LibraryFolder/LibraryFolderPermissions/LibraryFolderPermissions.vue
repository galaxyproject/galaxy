<template>
    <div>
        <div>
            <div v-if="folder">
                <b-button variant="primary" title="back to parent folder" :to="{ path: `/${this.folder.parent_id}` }">
                    <font-awesome-icon icon="angle-double-left" />
                </b-button>
                <div>
                    <div class="header text-center">{{ folder.name }}</div>
                </div>
            </div>
            <LibraryPermissionsWarning :is_admin="is_admin" />
            <hr class="my-4" />
            <b-container fluid>
                <div class="dataset_table">
                    <h2 class="text-center">Folder permissions</h2>
                    <PermissionsInputField
                        v-if="manage_folder_role_list"
                        :id="folder_id"
                        :permission_type="manage_type"
                        :initial_value="manage_folder_role_list"
                        :apiRootUrl="apiRootUrl"
                        alert="User with <strong>any</strong> of these roles can manage permissions on this folder."
                        title="Roles that can manage permissions on this folder"
                        @input="setUserPermissionsPreferences"
                    />

                    <PermissionsInputField
                        v-if="add_library_item_role_list"
                        :id="folder_id"
                        :permission_type="add_type"
                        :initial_value="add_library_item_role_list"
                        :apiRootUrl="apiRootUrl"
                        title="Roles that can add items to this folder"
                        alert="User with <strong>any</strong> of these roles can add items to this folder (folders and
                                datasets)."
                        @input="setUserPermissionsPreferences"
                    />

                    <PermissionsInputField
                        v-if="modify_folder_role_list"
                        :id="folder_id"
                        :permission_type="modify_type"
                        :initial_value="modify_folder_role_list"
                        :apiRootUrl="apiRootUrl"
                        title="Roles that can modify this folder"
                        alert="User with <strong>any</strong> of these roles can modify this folder (name, etc.)."
                        @input="setUserPermissionsPreferences"
                    />
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
            </b-container>
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
import LibraryPermissionsWarning from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryPermissionsWarning.vue";
import { extractRoles } from "./utils";

import { initPermissionsIcons } from "components/Libraries/icons";

Vue.use(BootstrapVue);
initPermissionsIcons();

export default {
    props: {
        folder_id: {
            type: String,
            required: true,
        },
    },
    components: {
        PermissionsInputField,
        LibraryPermissionsWarning,
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
            add_type: "add_library_item_role_list",
            manage_type: "manage_folder_role_list",
            modify_type: "modify_folder_role_list",
            apiRootUrl: `${getAppRoot()}api/folders`,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.is_admin = Galaxy.user.attributes.is_admin;
        this.services.getFolderPermissions(this.folder_id).then((fetched_permissions) => {
            this.add_library_item_role_list = extractRoles(fetched_permissions.add_library_item_role_list);
            this.manage_folder_role_list = extractRoles(fetched_permissions.manage_folder_role_list);
            this.modify_folder_role_list = extractRoles(fetched_permissions.modify_folder_role_list);
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
            this[permission_type] = ids;
        },
        postPermissions() {
            this.services.setPermissions(
                this.apiRootUrl,
                this.folder_id,
                [
                    { "add_ids[]": this.add_library_item_role_list },
                    { "manage_ids[]": this.manage_folder_role_list },
                    { "modify_ids[]": this.modify_folder_role_list },
                ],
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

<style scoped>
.header {
    font-size: 45px;
}
</style>
