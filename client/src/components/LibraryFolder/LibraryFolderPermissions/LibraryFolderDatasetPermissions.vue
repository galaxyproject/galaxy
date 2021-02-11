<template>
    <div>
        <div v-if="dataset">
            <b-button variant="primary" :to="{ path: `/${this.folder_id}` }">
                <font-awesome-icon icon="angle-double-left">1</font-awesome-icon>
            </b-button>
            <div>
                <div class="header text-center">{{ dataset.name }}</div>
            </div>
        </div>
        <LibraryPermissionsWarning :is_admin="is_admin" />
        <hr class="my-4" />
        <b-container fluid>
            <h2 class="text-center">Library-related permissions</h2>
            <PermissionsInputField
                v-if="modify_item_roles"
                :id="dataset_id"
                :permission_type="manage_type"
                :initial_value="modify_item_roles"
                title="Roles that can modify the library item"
                :apiRootUrl="apiRootUrl"
                alert="User with <strong>any</strong> of these roles can modify name, metadata, and other information about this library item."
                @input="setUserPermissionsPreferences"
            />
            <hr class="my-4" />
            <h2 class="text-center">Dataset-related permissions</h2>
            <div class="alert alert-warning text-center">
                Changes made below will affect <strong>every</strong> library item that was created from this dataset
                and also every history this dataset is part of.
            </div>
            <PermissionsInputField
                v-if="access_dataset_roles"
                :id="dataset_id"
                :permission_type="manage_type"
                :initial_value="access_dataset_roles"
                :apiRootUrl="apiRootUrl"
                title="Roles that can access the dataset"
                alert="User has to have <strong>all these roles</strong> in order to access this dataset.
                        Users without access permission <strong>cannot</strong> have other permissions on this dataset.
                        If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>."
                @input="setUserPermissionsPreferences"
            />
            <PermissionsInputField
                v-if="manage_dataset_roles"
                :id="dataset_id"
                :permission_type="manage_type"
                :initial_value="manage_dataset_roles"
                :apiRootUrl="apiRootUrl"
                title="Roles that can manage permissions on the dataset"
                alert="User with <strong>any</strong> of these roles can manage permissions of this dataset.
                        If you remove yourself you will lose the ability manage this dataset unless you are an admin."
                @input="setUserPermissionsPreferences"
            />
        </b-container>
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
import LibraryPermissionsWarning from "components/LibraryFolder/LibraryFolderPermissions/LibraryPermissionsWarning.vue";
import { extractRoles } from "./utils";

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
        dataset_id: {
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
            dataset: undefined,
            is_admin: undefined,
            access_dataset_roles: undefined,
            modify_item_roles: undefined,
            manage_dataset_roles: undefined,
            add_type: "add_type",
            manage_type: "manage_type",
            modify_type: "modify_type",
            apiRootUrl: `${getAppRoot()}api/libraries/datasets`,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.is_admin = Galaxy.user.attributes.is_admin;
        this.services.getDatasetPermissions(this.dataset_id).then((fetched_permissions) => {
            this.access_dataset_roles = extractRoles(fetched_permissions.access_dataset_roles);
            this.modify_item_roles = extractRoles(fetched_permissions.modify_item_roles);
            this.manage_dataset_roles = extractRoles(fetched_permissions.manage_dataset_roles);
        });
        this.services.getDataset(this.dataset_id).then((response) => {
            this.dataset = response;
        });
    },

    methods: {
        getParentLink() {
            return `${this.root}library/folders/${this.folder_id}`;
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
    },
};
</script>

<style scoped>
.header {
    font-size: 45px;
}
</style>
