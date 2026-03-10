<script setup lang="ts">
import { computed } from "vue";

import type { UserConcreteObjectStore } from "@/api/objectStores";
import type { TableField } from "@/components/Common/GTable.types";
import { DESCRIPTION_FIELD, NAME_FIELD, TEMPLATE_FIELD, TYPE_FIELD } from "@/components/ConfigTemplates/fields";
import { useInstanceTesting } from "@/components/ConfigTemplates/useConfigurationTesting";
import { useFiltering } from "@/components/ConfigTemplates/useInstanceFiltering";
import { useObjectStoreInstancesStore } from "@/stores/objectStoreInstancesStore";
import _l from "@/utils/localization";

import InstanceDropdown from "./InstanceDropdown.vue";
import GTable from "@/components/Common/GTable.vue";
import ManageIndexHeader from "@/components/ConfigTemplates/ManageIndexHeader.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";
import ObjectStoreTypeSpan from "@/components/ObjectStore/ObjectStoreTypeSpan.vue";
import TemplateSummarySpan from "@/components/ObjectStore/Templates/TemplateSummarySpan.vue";

const objectStoreInstancesStore = useObjectStoreInstancesStore();

interface Props {
    message?: string;
}

defineProps<Props>();

const BADGE_FIELD: TableField = {
    key: "badges",
    label: _l(" "),
    sortable: false,
};

const fields: TableField[] = [NAME_FIELD, DESCRIPTION_FIELD, TYPE_FIELD, TEMPLATE_FIELD, BADGE_FIELD];

const allItems = computed<UserConcreteObjectStore[]>(() => objectStoreInstancesStore.getInstances);
const { activeInstances } = useFiltering(allItems);
const loading = computed(() => objectStoreInstancesStore.loading);
objectStoreInstancesStore.fetchInstances();

function reload() {
    objectStoreInstancesStore.fetchInstances();
}

const testInstanceUrl = "/api/object_store_instances/{uuid}/test";

const { ConfigurationTestSummaryModal, showTestResults, testResults, test, testingError } =
    useInstanceTesting(testInstanceUrl);
</script>

<template>
    <div>
        <ManageIndexHeader header="Galaxy Storage" :message="message" create-route="/object_store_instances/create">
        </ManageIndexHeader>
        <ConfigurationTestSummaryModal v-model="showTestResults" :error="testingError" :test-results="testResults" />

        <GTable
            id="user-object-stores-index"
            caption-top
            fixed
            hover
            show-empty
            striped
            :fields="fields"
            :items="activeInstances">
            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="Loading Galaxy storage instances" />
                <b-alert v-else id="no-object-store-instances" variant="info" show>
                    <div>No Galaxy storage instances found, click the create button to configure a new one.</div>
                </b-alert>
            </template>
            <template v-slot:cell(badges)="{ item }">
                <ObjectStoreBadges size="1x" :badges="item.badges" />
            </template>
            <template v-slot:cell(name)="{ item }">
                <InstanceDropdown :object-store="item" @entryRemoved="reload" @test="test(item)" />
            </template>
            <template v-slot:cell(type)="{ item }">
                <ObjectStoreTypeSpan :type="item.type" />
            </template>
            <template v-slot:cell(template)="{ item }">
                <TemplateSummarySpan :template-version="item.template_version ?? 0" :template-id="item.template_id" />
            </template>
        </GTable>
    </div>
</template>
