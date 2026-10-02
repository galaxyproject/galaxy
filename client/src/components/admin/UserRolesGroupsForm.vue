<script setup lang="ts">
import "vue-multiselect/dist/vue-multiselect.min.css";

import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";
import Multiselect from "vue-multiselect";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface RoleOption {
    id: string;
    name: string;
}

interface GroupOption {
    id: string;
    name: string;
}

const props = defineProps<{
    userId: string;
}>();

const errorMessage = ref("");
const loading = ref(false);
// A form that failed to load must not be saved: it would replace the user's roles and groups with nothing.
const loadFailed = ref(false);
const email = ref("");
const selectedRoles = ref<RoleOption[]>([]);
const selectedGroups = ref<GroupOption[]>([]);
const roleOptions = ref<RoleOption[]>([]);
const groupOptions = ref<GroupOption[]>([]);
const roleSearch = ref("");

const router = useRouter();

// Assignable roles are few compared to users, so list them before anything is typed and search from the
// first character; short role names must stay reachable.
async function onRoleSearch(searchValue: string) {
    roleSearch.value = searchValue;
    const { data, error } = await GalaxyApi().GET("/api/roles", {
        params: { query: { search: searchValue || undefined, limit: 50, exclude_private: true } },
    });
    // A search is sent per keystroke; drop responses for queries the admin has typed past.
    if (searchValue !== roleSearch.value) {
        return;
    }
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }
    const selectedIds = new Set(selectedRoles.value.map((r) => r.id));
    const filtered = data.filter((r) => !selectedIds.has(r.id)).map((r) => ({ id: r.id, name: r.name }));
    roleOptions.value = [...selectedRoles.value, ...filtered];
}

async function loadData() {
    loading.value = true;
    const params = { path: { user_id: props.userId } };
    const [userResponse, rolesResponse, groupsResponse, allGroupsResponse] = await Promise.all([
        GalaxyApi().GET("/api/users/{user_id}", { params }),
        GalaxyApi().GET("/api/users/{user_id}/roles", { params }),
        GalaxyApi().GET("/api/users/{user_id}/groups", { params }),
        GalaxyApi().GET("/api/groups"),
    ]);
    const error = userResponse.error || rolesResponse.error || groupsResponse.error || allGroupsResponse.error;
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        loadFailed.value = true;
    } else {
        const user = userResponse.data!;
        email.value = "email" in user ? user.email : "";
        // The private role is kept by the server and cannot be assigned or removed here.
        selectedRoles.value = rolesResponse
            .data!.filter((r) => r.type !== "private")
            .map((r) => ({ id: r.id, name: r.name }));
        roleOptions.value = [...selectedRoles.value];
        selectedGroups.value = groupsResponse.data!.map((g) => ({ id: g.id, name: g.name }));
        groupOptions.value = allGroupsResponse.data!.map((g) => ({ id: g.id, name: g.name }));
        await onRoleSearch("");
    }
    loading.value = false;
}

async function onSubmit() {
    const params = { path: { user_id: props.userId } };
    const { error: rolesError } = await GalaxyApi().PUT("/api/users/{user_id}/roles", {
        params,
        body: { role_ids: selectedRoles.value.map((r) => r.id) },
    });
    if (rolesError) {
        errorMessage.value = errorMessageAsString(rolesError);
        return;
    }
    const { error: groupsError } = await GalaxyApi().PUT("/api/users/{user_id}/groups", {
        params,
        body: { group_ids: selectedGroups.value.map((g) => g.id) },
    });
    if (groupsError) {
        errorMessage.value = errorMessageAsString(groupsError);
        return;
    }
    router.push("/admin/users");
}

loadData();
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else id="admin-user-roles-groups-form">
            <GAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
            <template v-if="!loadFailed">
                <FormCard :title="`Roles and groups for '${email}'`" icon="fa-users">
                    <template v-slot:body>
                        <FormElementLabel id="admin-user-roles" title="Roles">
                            <Multiselect
                                id="admin-user-roles-select"
                                v-model="selectedRoles"
                                :options="roleOptions"
                                :clear-on-select="true"
                                :multiple="true"
                                :internal-search="false"
                                :max-height="300"
                                label="name"
                                track-by="id"
                                placeholder="Select or search roles..."
                                @search-change="onRoleSearch">
                                <template slot="noResult">
                                    <div>No roles found</div>
                                </template>
                                <template slot="noOptions">
                                    <div>No roles found</div>
                                </template>
                            </Multiselect>
                        </FormElementLabel>

                        <FormElementLabel id="admin-user-groups" title="Groups">
                            <Multiselect
                                id="admin-user-groups-select"
                                v-model="selectedGroups"
                                :options="groupOptions"
                                :clear-on-select="true"
                                :multiple="true"
                                :max-height="300"
                                label="name"
                                track-by="id"
                                placeholder="Select groups..." />
                        </FormElementLabel>
                    </template>
                </FormCard>
                <GButton id="admin-user-roles-groups-submit" class="my-2" color="blue" @click="onSubmit">
                    <FontAwesomeIcon :icon="faSave" class="mr-1" />
                    <span v-localize>Save</span>
                </GButton>
            </template>
        </div>
    </div>
</template>
