<template>
    <div>
        <b-container fluid>
            <div v-if="dataset">
                <b-breadcrumb>
                    <b-breadcrumb-item title="Return to the list of libraries" :to="{ path: `/` }">
                        Libraries
                    </b-breadcrumb-item>
                    <template v-for="path_item in this.dataset.full_path">
                        <b-breadcrumb-item
                            :key="path_item[0]"
                            :to="{ path: `/folders/${path_item[0]}` }"
                            :active="path_item[0] === dataset_id"
                            href="#"
                            >{{ path_item[1] }}</b-breadcrumb-item
                        >
                    </template>
                </b-breadcrumb>
                <b-row>
                    <b-col>
                        <b-button
                            data-toggle="tooltip"
                            data-placement="top"
                            title="Go to Dataset Details"
                            variant="secondary"
                            type="button"
                            :href="`${root}library/list#folders/${folder_id}/datasets/${dataset_id}`">
                            <font-awesome-icon :icon="['far', 'file']" />
                            &nbsp;Dataset Details
                        </b-button>
                    </b-col>
                    <b-col>
                        <div>
                            <div class="header text-center">{{ dataset.name }}</div>
                        </div>
                    </b-col>
                    <b-col />
                </b-row>
            </div>

            <LibraryPermissionsWarning :is_admin="is_admin" />
            <hr class="my-4" />
            <h2 class="text-center">Library-related permissions</h2>
            <PermissionsInputField
                v-if="modify_item_roles"
                :id="dataset_id"
                :permission_type="modify_item_roles_type"
                :initial_value="modify_item_roles"
                title="Roles that can modify the library item"
                :api-root-url="apiRootUrl"
                alert="User with <strong>any</strong> of these roles can modify name, metadata, and other information about this library item."
                @input="setUserPermissionsPreferences" />
            <hr class="my-4" />
            <h2 class="text-center">Dataset-related permissions</h2>
            <div class="alert alert-warning text-center">
                Changes made below will affect <strong>every</strong> library item that was created from this dataset
                and also every history this dataset is part of.
            </div>
            <p class="text-center" v-if="is_unrestricted">
                You can
                <strong @click="toggleDatasetPrivacy(true)" class="make-private">
                    <a id="make-private" href="javascript:void(0)">make this dataset private</a>
                </strong>
                to you.
            </p>
            <p class="text-center" v-else>
                You can
                <strong @click="toggleDatasetPrivacy(false)" class="remove-restrictions">
                    <a href="javascript:void(0)">remove all access restrictions</a>
                </strong>
                on this dataset.
            </p>

            <PermissionsInputField
                ref="access_field"
                v-if="access_dataset_roles"
                :id="dataset_id"
                :permission_type="access_dataset_roles_type"
                :initial_value="access_dataset_roles"
                :api-root-url="apiRootUrl"
                title="Roles that can access the dataset"
                alert="User has to have <strong>all these roles</strong> in order to access this dataset.
                        Users without access permission <strong>cannot</strong> have other permissions on this dataset.
                        If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>."
                @input="setUserPermissionsPreferences" />
            <PermissionsInputField
                v-if="manage_dataset_roles"
                :id="dataset_id"
                :permission_type="manage_dataset_roles_type"
                :initial_value="manage_dataset_roles"
                :api-root-url="apiRootUrl"
                title="Roles that can manage permissions on the dataset"
                alert="User with <strong>any</strong> of these roles can manage permissions of this dataset.
                        If you remove yourself you will lose the ability manage this dataset unless you are an admin."
                @input="setUserPermissionsPreferences" />
            <b-button
                data-toggle="tooltip"
                data-placement="top"
                title="Save modifications"
                class="toolbtn_save_permissions"
                variant="secondary"
                @click="postPermissions">
                <font-awesome-icon :icon="['far', 'save']" />
                &nbsp;Save
            </b-button>
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
import { getGalaxyInstance } from "app";
import PermissionsInputField from "components/Libraries/LibraryPermissions/PermissionsInputField";
import { initPermissionsIcons } from "components/Libraries/icons";
import LibraryPermissionsWarning from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryPermissionsWarning";
import { extractRoles } from "components/Libraries/library-utils";

import "vue-multiselect/dist/vue-multiselect.min.css";
import VueObserveVisibility from "vue-observe-visibility";

Vue.use(VueObserveVisibility);
Vue.use(BootstrapVue);
initPermissionsIcons();

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
            access_dataset_roles_type: "access_dataset_roles",
            modify_item_roles_type: "modify_item_roles",
            manage_dataset_roles_type: "manage_dataset_roles",
            apiRootUrl: `${getAppRoot()}api/libraries/datasets`,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.is_admin = Galaxy.user.attributes.is_admin;
        this.services
            .getDatasetPermissions(this.dataset_id)
            .then((fetched_permissions) => this.assignFetchedPermissions(fetched_permissions));
        this.services.getDataset(this.dataset_id).then((response) => {
            this.dataset = response;
        });
    },
    computed: {
        is_unrestricted() {
            return this.access_dataset_roles ? this.access_dataset_roles.length === 0 : false;
        },
    },
    methods: {
        assignFetchedPermissions(fetched_permissions) {
            this.access_dataset_roles = extractRoles(fetched_permissions.access_dataset_roles);
            this.modify_item_roles = extractRoles(fetched_permissions.modify_item_roles);
            this.manage_dataset_roles = extractRoles(fetched_permissions.manage_dataset_roles);
            console.log(this.access_dataset_roles);
        },
        toggleDatasetPrivacy(isMakePrivate) {
            this.services.toggleDatasetPrivacy(
                this.dataset_id,
                isMakePrivate,
                (fetched_permissions) => {
                    Toast.success(
                        `${
                            isMakePrivate
                                ? "The dataset is now private to you."
                                : "Access to this dataset is now unrestricted."
                        }`
                    );
                    this.assignFetchedPermissions(fetched_permissions);
                    this.$refs.access_field.assignValue(this.access_dataset_roles);
                },
                (error) => {
                    Toast.error("An error occurred while attempting to set folder permissions.");
                    console.error(error);
                }
            );
        },
        setUserPermissionsPreferences(ids, permission_type) {
            this[permission_type] = ids;
        },
        postPermissions() {
            this.services.setPermissions(
                this.apiRootUrl,
                this.dataset_id,
                [
                    { "access_ids[]": this.access_dataset_roles },
                    { "modify_ids[]": this.modify_item_roles },
                    { "manage_ids[]": this.manage_dataset_roles },
                ],
                (fetched_permissions) => {
                    Toast.success("Permissions saved.");
                    this.assignFetchedPermissions(fetched_permissions);
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
