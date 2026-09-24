<script setup lang="ts">
import "vue-multiselect/dist/vue-multiselect.min.css";

import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { ref } from "vue";
import Multiselect from "vue-multiselect";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import FormInput from "@/components/Form/Elements/FormInput.vue";
import FormSelection from "@/components/Form/Elements/FormSelection.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface UserOption {
    id: string;
    email: string;
}

interface GroupOption {
    id: string;
    name: string;
}

const props = defineProps<{
    roleId?: string;
}>();

const isEditMode = !!props.roleId;

const errorMessage = ref("");
const description = ref("");
const roleType = ref();
const loading = ref(false);
// A form that failed to load must not be saved: it would replace the role's associations with nothing.
const loadFailed = ref(false);
const name = ref("");
const savedName = ref("");
const selectedUsers = ref<UserOption[]>([]);
const selectedGroups = ref<GroupOption[]>([]);
const userOptions = ref<UserOption[]>([]);
const groupOptions = ref<GroupOption[]>([]);
const userSearch = ref("");
const roleTypes = [
    { value: "admin", label: "Default" },
    { value: "user_tool_execute", label: "Custom Tool Execution" },
    { value: "user_tool_create", label: "Custom Tool Creation" },
];

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
    // A search is sent per keystroke; drop responses for queries the admin has typed past.
    if (searchValue !== userSearch.value) {
        return;
    }
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }
    const selectedIds = new Set(selectedUsers.value.map((u) => u.id));
    const filtered = data.filter((u) => u.email && !selectedIds.has(u.id)).map((u) => ({ id: u.id, email: u.email! }));
    userOptions.value = [...selectedUsers.value, ...filtered];
}

async function loadRole(roleId: string) {
    const params = { path: { id: roleId } };
    const [roleResponse, usersResponse, groupsResponse] = await Promise.all([
        GalaxyApi().GET("/api/roles/{id}", { params }),
        GalaxyApi().GET("/api/roles/{id}/users", { params }),
        GalaxyApi().GET("/api/roles/{id}/groups", { params }),
    ]);
    const error = roleResponse.error || usersResponse.error || groupsResponse.error;
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        loadFailed.value = true;
        return;
    }
    name.value = savedName.value = roleResponse.data!.name;
    description.value = roleResponse.data!.description ?? "";
    selectedUsers.value = usersResponse.data!.map((u) => ({ id: u.id, email: u.email }));
    userOptions.value = [...selectedUsers.value];
    selectedGroups.value = groupsResponse.data!.map((g) => ({ id: g.id, name: g.name }));
}

async function fetchData() {
    loading.value = true;
    const { data: groups, error: groupsError } = await GalaxyApi().GET("/api/groups");
    if (groupsError) {
        errorMessage.value = errorMessageAsString(groupsError);
        loadFailed.value = true;
    } else {
        errorMessage.value = "";
        groupOptions.value = groups.map((g) => ({ id: g.id, name: g.name }));
        if (props.roleId) {
            await loadRole(props.roleId);
        }
    }
    loading.value = false;
}

async function onSubmit() {
    if (!name.value || (!isEditMode && !description.value)) {
        errorMessage.value = "Please complete all required inputs.";
        return;
    }
    const groupIds = selectedGroups.value.map((g) => g.id);
    const userIds = selectedUsers.value.map((u) => u.id);
    if (props.roleId) {
        const { error } = await GalaxyApi().PUT("/api/roles/{id}", {
            params: { path: { id: props.roleId } },
            body: {
                name: name.value,
                description: description.value,
                group_ids: groupIds,
                user_ids: userIds,
            },
        });
        if (error) {
            errorMessage.value = `Failed to update role: ${errorMessageAsString(error)}`;
            return;
        }
    } else {
        const { error } = await GalaxyApi().POST("/api/roles", {
            body: {
                name: name.value,
                description: description.value,
                group_ids: groupIds,
                user_ids: userIds,
                role_type: roleType.value,
            },
        });
        if (error) {
            errorMessage.value = `Failed to create role: ${errorMessageAsString(error)}`;
            return;
        }
    }
    router.push("/admin/roles");
}

fetchData();
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <template v-if="!loadFailed">
                <FormCard :title="isEditMode ? `Role '${savedName}'` : 'Create a new Role'" icon="fa-file-contract">
                    <template v-slot:body>
                        <FormElementLabel title="Name" :required="true" :condition="!!name">
                            <FormInput id="role-name" v-model="name" />
                        </FormElementLabel>
                        <FormElementLabel title="Description" :required="!isEditMode" :condition="!!description">
                            <FormInput id="role-description" v-model="description" />
                        </FormElementLabel>
                        <FormElementLabel v-if="!isEditMode" title="Role Type" :required="true">
                            <FormSelection id="role-type" v-model="roleType" :data="roleTypes" />
                        </FormElementLabel>
                        <FormElementLabel id="role-groups" title="Groups">
                            <Multiselect
                                id="role-groups-select"
                                v-model="selectedGroups"
                                :options="groupOptions"
                                :clear-on-select="true"
                                :multiple="true"
                                :max-height="300"
                                label="name"
                                track-by="id"
                                placeholder="Select groups..." />
                        </FormElementLabel>
                        <FormElementLabel id="role-users" title="Users">
                            <Multiselect
                                id="role-users-select"
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
                    </template>
                </FormCard>
                <GButton id="role-submit" class="my-2" color="blue" @click="onSubmit">
                    <FontAwesomeIcon :icon="faSave" class="mr-1" />
                    <span v-localize>{{ isEditMode ? "Save" : "Create" }}</span>
                </GButton>
            </template>
        </div>
    </div>
</template>
