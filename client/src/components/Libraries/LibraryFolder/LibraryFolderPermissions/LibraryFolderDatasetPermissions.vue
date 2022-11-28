<template>
    <div>
        <b-container fluid>
            <div v-if="dataset">
                <LibraryBreadcrumb :current-id="dataset_id" :full_path="dataset.full_path" />
                <b-button
                    data-toggle="tooltip"
                    data-placement="top"
                    title="Go to Dataset Details"
                    variant="secondary"
                    type="button"
                    :href="`${root}libraries/folders/${folder_id}/dataset/${dataset_id}`">
                    <font-awesome-icon :icon="['far', 'file']" />
                    &nbsp;Dataset Details
                </b-button>
                <PermissionsHeader :name="dataset.name" />
            </div>

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
            <p v-if="is_unrestricted" class="text-center">
                You can
                <strong class="make-private" @click="toggleDatasetPrivacy(true)">
                    <a id="make-private" href="javascript:void(0)">make this dataset private</a>
                </strong>
                to you.
            </p>
            <p v-else class="text-center">
                You can
                <strong class="remove-restrictions" @click="toggleDatasetPrivacy(false)">
                    <a href="javascript:void(0)">remove all access restrictions</a>
                </strong>
                on this dataset.
            </p>

            <PermissionsInputField
                v-if="access_dataset_roles"
                :id="dataset_id"
                ref="access_field"
                :permission_type="access_dataset_roles_type"
                :initial_value="access_dataset_roles"
                :api-root-url="apiRootUrl"
                title="Roles that can access the dataset"
                alert="User has to have <strong>all these roles</strong> in order to access this dataset.
                        Users without access permission <strong>cannot</strong> have other permissions on this dataset.
                        If there are no access roles set on the dataset it is considered <strong>unrestricted</strong>."
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
import { Toast } from "composables/toast";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import PermissionsHeader from "components/Libraries/LibraryPermissions/PermissionsHeader";
import PermissionsInputField from "components/Libraries/LibraryPermissions/PermissionsInputField";
import { initPermissionsIcons } from "components/Libraries/icons";
import { extractRoles } from "components/Libraries/library-utils";
import LibraryBreadcrumb from "components/Libraries/LibraryFolder/LibraryBreadcrumb";

import "vue-multiselect/dist/vue-multiselect.min.css";
import VueObserveVisibility from "vue-observe-visibility";

Vue.use(VueObserveVisibility);
Vue.use(BootstrapVue);
initPermissionsIcons();

export default {
    components: {
        PermissionsInputField,
        FontAwesomeIcon,
        LibraryBreadcrumb,
        PermissionsHeader,
    },
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
    data() {
        return {
            permissions: undefined,
            dataset: undefined,
            is_admin: undefined,
            access_dataset_roles: undefined,
            modify_item_roles: undefined,
            access_dataset_roles_type: "access_dataset_roles",
            modify_item_roles_type: "modify_item_roles",
            apiRootUrl: `${getAppRoot()}api/libraries/datasets`,
        };
    },
    computed: {
        is_unrestricted() {
            return this.access_dataset_roles ? this.access_dataset_roles.length === 0 : false;
        },
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
    methods: {
        assignFetchedPermissions(fetched_permissions) {
            this.access_dataset_roles = extractRoles(fetched_permissions.access_dataset_roles);
            this.modify_item_roles = extractRoles(fetched_permissions.modify_item_roles);
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
                [{ "access_ids[]": this.access_dataset_roles }, { "modify_ids[]": this.modify_item_roles }],
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
