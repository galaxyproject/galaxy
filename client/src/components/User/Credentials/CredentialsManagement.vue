<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { isRegisteredUser } from "@/api";
import { Toast } from "@/composables/toast";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";
import Filtering, { contains } from "@/utils/filtering";
import { errorMessageAsString } from "@/utils/simple-error";

import GLink from "@/components/BaseComponents/GLink.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ServiceCredentialsGroupsList from "@/components/User/Credentials/ServiceCredentialsGroupsList.vue";

const breadcrumbItems = [{ title: "User Preferences", to: "/user" }, { title: "Tools Credentials Management" }];

const credentialsFilterClass = new Filtering({
    name: { placeholder: "credential group name", type: String, handler: contains("name"), menuItem: true },
    tool: { placeholder: "tool name", type: String, handler: contains("tool"), menuItem: true },
    service: { placeholder: "service name", type: String, handler: contains("service"), menuItem: true },
});

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const { getToolNameById } = useToolStore();

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { isBusy, busyMessage, userToolsGroups } = storeToRefs(userToolsServiceCredentialsStore);

const filterText = ref("");
const showAdvanced = ref(false);

const filteredUserToolsGroups = computed(() => {
    if (!filterText.value) {
        return userToolsGroups.value;
    }

    const filters = {
        name: credentialsFilterClass.getFilterValue(filterText.value, "name") as string,
        tool: credentialsFilterClass.getFilterValue(filterText.value, "tool") as string,
        service: credentialsFilterClass.getFilterValue(filterText.value, "service") as string,
    };

    const hasFilterSyntax = Boolean(filters.name && (filters.tool || filters.service));

    const generalSearch = filterText.value.toLowerCase();

    return userToolsGroups.value.filter((group) => {
        const searchableValues = {
            groupName: group.name?.toLowerCase() || "",
            serviceName: group.serviceDefinition.name?.toLowerCase() || "",
            toolName: getToolNameById(group.sourceId)?.toLowerCase() || "",
        };

        if (hasFilterSyntax) {
            return matchesSpecificFilters(filters, searchableValues);
        } else {
            return matchesGeneralSearch(generalSearch, searchableValues);
        }
    });
});

const noItems = computed(() => !isBusy.value && filteredUserToolsGroups.value.length === 0 && !filterText.value);
const noResults = computed(
    () => !isBusy.value && filteredUserToolsGroups.value.length === 0 && Boolean(filterText.value),
);
const rawFilters = computed(() =>
    Object.fromEntries(credentialsFilterClass.getFiltersForText(filterText.value, true, false)),
);
const validFilters = computed(() => credentialsFilterClass.getValidFilters(rawFilters.value, true).validFilters);
const invalidFilters = computed(() => credentialsFilterClass.getValidFilters(rawFilters.value, true).invalidFilters);
const isSurroundedByQuotes = computed(() => /^["'].*["']$/.test(filterText.value));
const hasInvalidFilters = computed(() => !isSurroundedByQuotes.value && Object.keys(invalidFilters.value).length > 0);

function matchesSpecificFilters(
    filters: { name: string; tool: string; service: string },
    values: { groupName: string; serviceName: string; toolName: string },
): boolean {
    const { name: nameFilter, tool: toolFilter, service: serviceFilter } = filters;
    const { groupName, serviceName, toolName } = values;

    if (toolFilter && !toolName.includes(toolFilter.toLowerCase())) {
        return false;
    }

    if (serviceFilter && !serviceName.includes(serviceFilter.toLowerCase())) {
        return false;
    }

    if (nameFilter && !groupName.includes(nameFilter.toLowerCase())) {
        return false;
    }

    return true;
}

function matchesGeneralSearch(
    searchTerm: string,
    values: { groupName: string; serviceName: string; toolName: string },
): boolean {
    const { groupName, serviceName, toolName } = values;

    return groupName.includes(searchTerm) || serviceName.includes(searchTerm) || toolName.includes(searchTerm);
}

function validatedFilterText() {
    if (isSurroundedByQuotes.value) {
        // the `filterText` is surrounded by quotes, remove them
        return filterText.value.slice(1, -1);
    } else if (Object.keys(rawFilters.value).length === 0) {
        // there are no filters derived from the `filterText`
        return filterText.value;
    }
    // there are valid filters derived from the `filterText`
    return credentialsFilterClass.getFilterText(validFilters.value, true);
}

async function fetchData() {
    if (isRegisteredUser(currentUser.value)) {
        try {
            await userToolsServiceCredentialsStore.fetchAllUserToolsServiceCredentials();
        } catch (error) {
            Toast.error(`${errorMessageAsString(error)}. Could not fetch your credentials for data.`);
        }
    }
}

watch(
    () => currentUser.value,
    async () => {
        await fetchData();
    },
    { immediate: true },
);
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <div class="mb-2">You can manage your provided credentials for tools here.</div>

        <FilterMenu
            id="credentials-filter-menu"
            class="mb-2"
            name="Credentials Groups"
            :filter-class="credentialsFilterClass"
            :filter-text.sync="filterText"
            :loading="isBusy"
            :show-advanced.sync="showAdvanced"
            placeholder="Search credentials groups by name, tool, or service" />

        <BAlert v-if="isBusy" show>
            <LoadingSpan :message="busyMessage" />
        </BAlert>
        <BAlert v-else-if="noItems" variant="info" show>
            No credentials have been defined for any tools or services yet.
        </BAlert>
        <BAlert v-else-if="hasInvalidFilters" variant="danger" show>
            <Heading h4 inline size="sm">Invalid filters in query:</Heading>
            <ul class="mb-0">
                <li v-for="[invalidKey, value] in Object.entries(invalidFilters)" :key="invalidKey">
                    <strong>{{ invalidKey }}</strong>
                    : {{ value }}
                </li>
            </ul>
            <GLink @click="filterText = validatedFilterText()"> Remove invalid filters from query </GLink>
            or
            <GLink
                title="Note that this might produce inaccurate results"
                tooltip
                @click="filterText = `'${filterText}'`">
                Match the exact query provided
            </GLink>
        </BAlert>
        <BAlert v-else-if="noResults" variant="info" show>
            No credentials group found matching: <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>
        <div v-else-if="!isBusy">
            <ServiceCredentialsGroupsList :service-groups="filteredUserToolsGroups" />
        </div>
    </div>
</template>
