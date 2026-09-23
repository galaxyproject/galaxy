<script setup lang="ts">
import "vue-multiselect/dist/vue-multiselect.min.css";

import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { ref } from "vue";
import Multiselect from "vue-multiselect";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

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
    quotaId: string;
}>();

const errorMessage = ref("");
const loading = ref(false);
const quotaName = ref("");
const selectedUsers = ref<UserOption[]>([]);
const selectedGroups = ref<GroupOption[]>([]);
const userOptions = ref<UserOption[]>([]);
const groupOptions = ref<GroupOption[]>([]);
const userSearch = ref("");

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

async function loadQuotaData() {
    loading.value = true;
    try {
        const { data: quota, error: quotaError } = await GalaxyApi().GET("/api/quotas/{id}", {
            params: { path: { id: props.quotaId } },
        });
        if (quotaError) {
            errorMessage.value = errorMessageAsString(quotaError);
            loading.value = false;
            return;
        }
        quotaName.value = quota.name;
        selectedUsers.value = quota.users.map((a) => ({ id: a.user.id, email: a.user.email }));
        userOptions.value = [...selectedUsers.value];
        selectedGroups.value = quota.groups.map((a) => ({ id: a.group.id, name: a.group.name }));

        const { data: groups, error: groupsError } = await GalaxyApi().GET("/api/groups");
        if (groupsError) {
            errorMessage.value = errorMessageAsString(groupsError);
            loading.value = false;
            return;
        }
        groupOptions.value = groups.map((g) => ({ id: g.id, name: g.name }));
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
    loading.value = false;
}

async function onSubmit() {
    const { error } = await GalaxyApi().PUT("/api/quotas/{id}", {
        params: { path: { id: props.quotaId } },
        body: {
            operation: "=",
            in_users: selectedUsers.value.map((u) => u.id),
            in_groups: selectedGroups.value.map((g) => g.id),
        },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }
    router.push("/admin/quotas");
}

loadQuotaData();
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <FormCard :title="`Quota '${quotaName}'`" icon="fa-database">
                <template v-slot:body>
                    <FormElementLabel title="Groups">
                        <Multiselect
                            id="admin-quota-groups-select"
                            v-model="selectedGroups"
                            :options="groupOptions"
                            :clear-on-select="true"
                            :multiple="true"
                            :max-height="300"
                            label="name"
                            track-by="id"
                            placeholder="Select groups..." />
                    </FormElementLabel>

                    <FormElementLabel title="Users">
                        <Multiselect
                            id="admin-quota-users-select"
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
            <BButton id="admin-quota-submit" class="my-2" variant="primary" @click="onSubmit">
                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                <span v-localize>Save</span>
            </BButton>
        </div>
    </div>
</template>
