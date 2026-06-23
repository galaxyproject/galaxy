<script setup lang="ts">
import "vue-multiselect/dist/vue-multiselect.min.css";

import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormCheckbox } from "bootstrap-vue";
import { ref } from "vue";
import Multiselect from "vue-multiselect";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import FormInput from "@/components/Form/Elements/FormInput.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface UserOption {
    id: string;
    email: string;
}

interface RoleOption {
    id: string;
    name: string;
}

const props = defineProps<{
    groupId?: string;
}>();

const isEditMode = !!props.groupId;

const errorMessage = ref("");
const loading = ref(false);
const groupName = ref("");
const selectedUsers = ref<UserOption[]>([]);
const selectedRoles = ref<RoleOption[]>([]);
const userOptions = ref<UserOption[]>([]);
const roleOptions = ref<RoleOption[]>([]);
const userSearch = ref("");
const roleSearch = ref("");
const autoCreateRole = ref(false);

const router = useRouter();

async function onUserSearch(searchValue: string) {
    userSearch.value = searchValue;
    if (searchValue.length < 3) {
        userOptions.value = [...selectedUsers.value];
        return;
    }
    const { data, error } = await GalaxyApi().GET("/api/users", {
        params: { query: { f_email: searchValue, limit: 50 } },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }
    const selectedIds = new Set(selectedUsers.value.map((u) => u.id));
    const filtered = data.filter((u) => u.email && !selectedIds.has(u.id)).map((u) => ({ id: u.id, email: u.email! }));
    userOptions.value = [...selectedUsers.value, ...filtered];
}

async function onRoleSearch(searchValue: string) {
    roleSearch.value = searchValue;
    if (searchValue.length < 3) {
        roleOptions.value = [...selectedRoles.value];
        return;
    }
    const { data, error } = await GalaxyApi().GET("/api/roles", {
        params: { query: { search: searchValue, limit: 50 } },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }
    const selectedIds = new Set(selectedRoles.value.map((r) => r.id));
    const filtered = data.filter((r) => !selectedIds.has(r.id)).map((r) => ({ id: r.id, name: r.name }));
    roleOptions.value = [...selectedRoles.value, ...filtered];
}

async function loadGroupData() {
    if (!props.groupId) {
        return;
    }
    loading.value = true;
    try {
        const { data: group, error: groupError } = await GalaxyApi().GET("/api/groups/{group_id}", {
            params: { path: { group_id: props.groupId } },
        });
        if (groupError) {
            errorMessage.value = errorMessageAsString(groupError);
            loading.value = false;
            return;
        }
        groupName.value = group.name;

        const { data: users, error: usersError } = await GalaxyApi().GET("/api/groups/{group_id}/users", {
            params: { path: { group_id: props.groupId } },
        });
        if (usersError) {
            errorMessage.value = errorMessageAsString(usersError);
            loading.value = false;
            return;
        }
        selectedUsers.value = users.map((u) => ({
            id: u.id,
            email: u.email,
        }));
        userOptions.value = [...selectedUsers.value];

        const { data: roles, error: rolesError } = await GalaxyApi().GET("/api/groups/{group_id}/roles", {
            params: { path: { group_id: props.groupId } },
        });
        if (rolesError) {
            errorMessage.value = errorMessageAsString(rolesError);
            loading.value = false;
            return;
        }
        selectedRoles.value = roles.map((r) => ({
            id: r.id,
            name: r.name,
        }));
        roleOptions.value = [...selectedRoles.value];
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
    loading.value = false;
}

async function onSubmit() {
    const userIds = selectedUsers.value.map((u) => u.id);
    const roleIds = selectedRoles.value.map((r) => r.id);

    if (isEditMode) {
        const { error } = await GalaxyApi().PUT("/api/groups/{group_id}", {
            params: { path: { group_id: props.groupId! } },
            body: {
                user_ids: userIds,
                role_ids: roleIds,
            },
        });
        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return;
        }
    } else {
        if (!groupName.value) {
            errorMessage.value = "Please enter a group name.";
            return;
        }
        const { error } = await GalaxyApi().POST("/api/groups", {
            body: {
                name: groupName.value,
                user_ids: userIds,
                role_ids: roleIds,
                auto_create_role: autoCreateRole.value,
            },
        });
        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return;
        }
    }
    router.push("/admin/groups");
}

loadGroupData();
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <FormCard :title="isEditMode ? `Group '${groupName}'` : 'Create a new Group'" icon="fa-users">
                <template v-slot:body>
                    <FormElementLabel title="Name" :required="!isEditMode" :condition="!!groupName">
                        <FormInput v-if="!isEditMode" id="admin-group-name-input" v-model="groupName" />
                        <span v-else>{{ groupName }}</span>
                    </FormElementLabel>

                    <FormElementLabel title="Users">
                        <Multiselect
                            id="admin-group-users-select"
                            v-model="selectedUsers"
                            :options="userOptions"
                            :clear-on-select="true"
                            :multiple="true"
                            :internal-search="false"
                            :max-height="300"
                            label="email"
                            track-by="id"
                            placeholder="Search users by email..."
                            @search-change="onUserSearch">
                            <template slot="noResult">
                                <div v-if="userSearch.length < 3">Enter at least 3 characters to search</div>
                                <div v-else>No users found</div>
                            </template>
                            <template slot="noOptions">
                                <div>Enter at least 3 characters to search</div>
                            </template>
                        </Multiselect>
                    </FormElementLabel>

                    <FormElementLabel title="Roles">
                        <Multiselect
                            id="admin-group-roles-select"
                            v-model="selectedRoles"
                            :options="roleOptions"
                            :clear-on-select="true"
                            :multiple="true"
                            :internal-search="false"
                            :max-height="300"
                            label="name"
                            track-by="id"
                            placeholder="Search roles by name..."
                            @search-change="onRoleSearch">
                            <template slot="noResult">
                                <div v-if="roleSearch.length < 3">Enter at least 3 characters to search</div>
                                <div v-else>No roles found</div>
                            </template>
                            <template slot="noOptions">
                                <div>Enter at least 3 characters to search</div>
                            </template>
                        </Multiselect>
                    </FormElementLabel>

                    <FormElementLabel v-if="!isEditMode" title="Auto-create role">
                        <BFormCheckbox v-model="autoCreateRole">
                            Create a new role with the same name as this group
                        </BFormCheckbox>
                    </FormElementLabel>
                </template>
            </FormCard>
            <BButton id="admin-group-submit" class="my-2" variant="primary" @click="onSubmit">
                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                <span v-localize>{{ isEditMode ? "Save" : "Create" }}</span>
            </BButton>
        </div>
    </div>
</template>
