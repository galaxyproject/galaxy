<template>
    <div>
        <b-button variant="link" @click="onGoBack">Go back to Libraries</b-button>
        <PermissionsHeader v-if="library" :name="library.name" />
        <h2 class="text-center">Library permissions</h2>
        <PermissionsInputField
            v-if="access_library_role_list"
            :id="library_id"
            :permission_type="access_type"
            :initial_value="access_library_role_list"
            :api-root-url="apiRootUrl"
            alert="User with <strong>any</strong> of these roles can access this library. If there are no access roles set on the library it is considered <strong>unrestricted</strong>."
            title="Roles that can access the library"
            @input="setUserPermissionsPreferences" />
        <PermissionsInputField
            v-if="add_library_item_role_list"
            :id="library_id"
            :permission_type="add_type"
            :initial_value="add_library_item_role_list"
            :api-root-url="apiRootUrl"
            class="add_perm"
            alert="User with <strong>any</strong> of these roles can add items to this library (folders and datasets)."
            title="Roles that can add items to this library"
            @input="setUserPermissionsPreferences" />
        <PermissionsInputField
            v-if="modify_library_role_list"
            :id="library_id"
            :permission_type="modify_type"
            :initial_value="modify_library_role_list"
            :api-root-url="apiRootUrl"
            alert="User with  <strong>any</strong> of these roles can modify this library (name, synopsis, etc.)."
            title="Roles that can modify this library"
            @input="setUserPermissionsPreferences" />
        <button title="Save modifications" class="toolbtn_save_permissions" @click="postPermissions">
            <font-awesome-icon :icon="['far', 'save']" />
            Save
        </button>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "components/Libraries/LibraryPermissions/services";
import { Toast } from "ui/toast";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import PermissionsHeader from "components/Libraries/LibraryPermissions/PermissionsHeader";
import { extractRoles } from "components/Libraries/library-utils";
import { initPermissionsIcons } from "components/Libraries/icons";
import PermissionsInputField from "components/Libraries/LibraryPermissions/PermissionsInputField";

Vue.use(BootstrapVue);
initPermissionsIcons();

export default {
    components: {
        PermissionsHeader,
        PermissionsInputField,
        FontAwesomeIcon,
    },
    props: {
        library_id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            permissions: undefined,
            library: undefined,
            add_library_item_role_list: undefined,
            modify_library_role_list: undefined,
            access_library_role_list: undefined,
            apiRootUrl: `${getAppRoot()}api/libraries`,
            add_type: "add_library_item_role_list",
            modify_type: "modify_library_role_list",
            access_type: "access_library_role_list",
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getLibraryPermissions(this.library_id).then((fetched_permissions) => {
            console.log("fetched_permissions", fetched_permissions);
            this.add_library_item_role_list = extractRoles(fetched_permissions.add_library_item_role_list);
            this.modify_library_role_list = extractRoles(fetched_permissions.modify_library_role_list);
            this.access_library_role_list = extractRoles(fetched_permissions.access_library_role_list);
        });
        this.services.getLibrary(this.library_id).then((library) => {
            this.library = library;
        });
    },

    methods: {
        setUserPermissionsPreferences(ids, permission_type) {
            this[permission_type] = ids;
        },
        postPermissions() {
            this.services.setPermissions(
                this.apiRootUrl,
                this.library_id,
                [
                    { "add_ids[]": this.add_library_item_role_list },
                    { "modify_ids[]": this.modify_library_role_list },
                    { "access_ids[]": this.access_library_role_list },
                ],
                (fetched_permissions) => {
                    Toast.success("Library permissions saved.");
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
