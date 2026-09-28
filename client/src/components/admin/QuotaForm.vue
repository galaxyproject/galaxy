<script setup lang="ts">
import "vue-multiselect/dist/vue-multiselect.min.css";

import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { useConfig } from "@/composables/config";
import { errorMessageAsString } from "@/utils/simple-error";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
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

type QuotaOperation = "=" | "+" | "-";
type DefaultQuotaValue = "no" | "registered" | "unregistered";

const DEFAULT_QUOTA_SOURCE = "__default__";
const AMOUNT_HELP = 'Examples: "10000MB", "99 gb", "0.2T", "unlimited"';

const props = defineProps<{
    quotaId?: string;
}>();

const isEditMode = !!props.quotaId;

const { config } = useConfig();

const errorMessage = ref("");
const loading = ref(false);
// A form that failed to load must not be saved: it would replace the quota's associations with nothing.
const loadFailed = ref(false);
const quotaName = ref("");
const savedQuotaName = ref("");
const savedAmount = ref("");
const savedOperation = ref<QuotaOperation>("=");
const savedDefaultType = ref<DefaultQuotaValue>("no");
const description = ref("");
const amount = ref("");
const operation = ref<QuotaOperation>("=");
const defaultType = ref<DefaultQuotaValue>("no");
const quotaSourceLabel = ref(DEFAULT_QUOTA_SOURCE);
const selectedUsers = ref<UserOption[]>([]);
const selectedGroups = ref<GroupOption[]>([]);
const userOptions = ref<UserOption[]>([]);
const groupOptions = ref<GroupOption[]>([]);
const userSearch = ref("");

const operationOptions = [
    { value: "=", label: "=" },
    { value: "+", label: "+" },
    { value: "-", label: "-" },
];
const defaultOptions = [
    { value: "no", label: "No" },
    { value: "registered", label: "Yes, registered" },
    { value: "unregistered", label: "Yes, unregistered" },
];
const quotaSourceOptions = computed(() => {
    const labels: string[] = config.value?.quota_source_labels ?? [];
    return [
        { value: DEFAULT_QUOTA_SOURCE, label: "Default Quota" },
        ...labels.map((label) => ({ value: label, label })),
    ];
});

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

async function loadData() {
    loading.value = true;
    try {
        if (props.quotaId) {
            const { data: quota, error: quotaError } = await GalaxyApi().GET("/api/quotas/{id}", {
                params: { path: { id: props.quotaId } },
            });
            if (quotaError) {
                errorMessage.value = errorMessageAsString(quotaError);
                loadFailed.value = true;
                loading.value = false;
                return;
            }
            quotaName.value = savedQuotaName.value = quota.name;
            description.value = quota.description;
            amount.value = savedAmount.value = quota.display_amount;
            operation.value = savedOperation.value = quota.operation;
            defaultType.value = savedDefaultType.value = quota.default[0]?.type ?? "no";
            selectedUsers.value = quota.users.map((a) => ({ id: a.user.id, email: a.user.email }));
            userOptions.value = [...selectedUsers.value];
            selectedGroups.value = quota.groups.map((a) => ({ id: a.group.id, name: a.group.name }));
        }

        const { data: groups, error: groupsError } = await GalaxyApi().GET("/api/groups");
        if (groupsError) {
            errorMessage.value = errorMessageAsString(groupsError);
            loadFailed.value = true;
            loading.value = false;
            return;
        }
        groupOptions.value = groups.map((g) => ({ id: g.id, name: g.name }));
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
        loadFailed.value = true;
    }
    loading.value = false;
}

async function onSubmit() {
    const userIds = selectedUsers.value.map((u) => u.id);
    const groupIds = selectedGroups.value.map((g) => g.id);

    if (!quotaName.value || (!isEditMode && !description.value) || !amount.value) {
        errorMessage.value = isEditMode
            ? "Please enter a name and amount."
            : "Please enter a name, description and amount.";
        return;
    }
    if (props.quotaId) {
        // The displayed amount is rounded, so only send it back when the admin changed it.
        const amountChanged = amount.value !== savedAmount.value || operation.value !== savedOperation.value;
        const { error } = await GalaxyApi().PUT("/api/quotas/{id}", {
            params: { path: { id: props.quotaId } },
            body: {
                name: quotaName.value,
                description: description.value,
                // The operation is only applied together with an amount.
                operation: operation.value,
                ...(amountChanged ? { amount: amount.value } : {}),
                ...(defaultType.value !== savedDefaultType.value ? { default: defaultType.value } : {}),
                // Default quotas cannot have users or groups; making a quota a default drops them server side.
                ...(defaultType.value === "no" ? { in_users: userIds, in_groups: groupIds } : {}),
            },
        });
        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return;
        }
    } else {
        const { error } = await GalaxyApi().POST("/api/quotas", {
            body: {
                name: quotaName.value,
                description: description.value,
                amount: amount.value,
                operation: operation.value,
                default: defaultType.value,
                quota_source_label: quotaSourceLabel.value === DEFAULT_QUOTA_SOURCE ? null : quotaSourceLabel.value,
                in_users: userIds,
                in_groups: groupIds,
            },
        });
        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return;
        }
    }
    router.push("/admin/quotas");
}

loadData();
</script>

<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else id="admin-quota-form">
            <GAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
            <template v-if="!loadFailed">
                <FormCard :title="isEditMode ? `Quota '${savedQuotaName}'` : 'Create Quota'" icon="fa-database">
                    <template v-slot:body>
                        <FormElementLabel title="Name" :required="true" :condition="!!quotaName">
                            <GFormInput id="admin-quota-name" v-model="quotaName" />
                        </FormElementLabel>
                        <FormElementLabel title="Description" :required="!isEditMode" :condition="!!description">
                            <GFormInput id="admin-quota-description" v-model="description" />
                        </FormElementLabel>
                        <FormElementLabel title="Amount" :required="true" :condition="!!amount" :help="AMOUNT_HELP">
                            <GFormInput id="admin-quota-amount" v-model="amount" />
                        </FormElementLabel>
                        <FormElementLabel title="Assign, increase by amount, or decrease by amount?">
                            <FormSelection id="admin-quota-operation" v-model="operation" :data="operationOptions" />
                        </FormElementLabel>
                        <FormElementLabel
                            title="Is this quota a default for a class of users (if yes, what type)?"
                            help="Default quotas cannot be associated with specific users and groups.">
                            <FormSelection id="admin-quota-default" v-model="defaultType" :data="defaultOptions" />
                        </FormElementLabel>
                        <FormElementLabel
                            v-if="!isEditMode && quotaSourceOptions.length > 1"
                            title="Apply quota to labeled object stores.">
                            <FormSelection
                                id="admin-quota-source-label"
                                v-model="quotaSourceLabel"
                                :data="quotaSourceOptions" />
                        </FormElementLabel>

                        <template v-if="defaultType === 'no'">
                            <FormElementLabel id="admin-quota-groups" title="Groups">
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

                            <FormElementLabel id="admin-quota-users" title="Users">
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
                    </template>
                </FormCard>
                <GButton id="admin-quota-submit" class="my-2" color="blue" @click="onSubmit">
                    <FontAwesomeIcon :icon="faSave" class="mr-1" />
                    <span v-localize>{{ isEditMode ? "Save" : "Create" }}</span>
                </GButton>
            </template>
        </div>
    </div>
</template>
