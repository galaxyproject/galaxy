<template>
    <div>
        <b-button variant="link" @click="onGoBack">Go back</b-button>
        <PermissionsHeader v-if="folder" :name="folder.name" />
        <b-container fluid>
            <div class="dataset_table">
                <h2 class="text-center">Folder permissions</h2>
                <PermissionsInputField
                    v-if="add_library_item_role_list"
                    :id="folder_id"
                    :permission_type="add_type"
                    :initial_value="add_library_item_role_list"
                    :api-root-url="apiRootUrl"
                    title="Roles that can add items to this folder"
                    alert="User with <strong>any</strong> of these roles can add items to this folder (folders and
                                datasets)."
                    @input="setUserPermissionsPreferences" />
                <PermissionsInputField
                    v-if="modify_folder_role_list"
                    :id="folder_id"
                    :permission_type="modify_type"
                    :initial_value="modify_folder_role_list"
                    :api-root-url="apiRootUrl"
                    title="Roles that can modify this folder"
                    alert="User with <strong>any</strong> of these roles can modify this folder (name, etc.)."
                    @input="setUserPermissionsPreferences" />
                <button
                    data-toggle="tooltip"
                    data-placement="top"
                    title="Save modifications"
                    class="btn btn-secondary toolbtn_save_permissions primary-button"
                    type="button"
                    @click="postPermissions">
                    <font-awesome-icon :icon="['far', 'save']" />
                    &nbsp;Save
                </button>
            </div>
        </b-container>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "components/Libraries/LibraryPermissions/services";
import { Toast } from "ui/toast";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import PermissionsInputField from "components/Libraries/LibraryPermissions/PermissionsInputField";
import PermissionsHeader from "components/Libraries/LibraryPermissions/PermissionsHeader";
import { extractRoles } from "components/Libraries/library-utils";

import { initPermissionsIcons } from "components/Libraries/icons";

Vue.use(BootstrapVue);
initPermissionsIcons();

export default {
    components: {
        PermissionsInputField,
        PermissionsHeader,
        FontAwesomeIcon,
    },
    props: {
        folder_id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            permissions: undefined,
            folder: undefined,
            add_library_item_role_list: undefined,
            modify_folder_role_list: undefined,
            add_type: "add_library_item_role_list",
            modify_type: "modify_folder_role_list",
            apiRootUrl: `${getAppRoot()}api/folders`,
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getFolderPermissions(this.folder_id).then((fetched_permissions) => {
            this.add_library_item_role_list = extractRoles(fetched_permissions.add_library_item_role_list);
            this.modify_folder_role_list = extractRoles(fetched_permissions.modify_folder_role_list);
        });
        this.services.getFolder(this.folder_id).then((response) => {
            this.folder = response;
        });
    },

    methods: {
        setUserPermissionsPreferences(ids, permission_type) {
            this[permission_type] = ids;
        },
        postPermissions() {
            this.services.setPermissions(
                this.apiRootUrl,
                this.folder_id,
                [{ "add_ids[]": this.add_library_item_role_list }, { "modify_ids[]": this.modify_folder_role_list }],
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
        onGoBack() {
            this.$router.go(-1);
        },
    },
};
</script>
