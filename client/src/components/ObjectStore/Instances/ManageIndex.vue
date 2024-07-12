<script setup lang="ts">
import { BTable } from "bootstrap-vue";
import { computed } from "vue";

import type { UserConcreteObjectStore } from "@/api/objectStores";
import { DESCRIPTION_FIELD, NAME_FIELD, TEMPLATE_FIELD, TYPE_FIELD } from "@/components/ConfigTemplates/fields";
import { useFiltering } from "@/components/ConfigTemplates/useInstanceFiltering";
import { useObjectStoreInstancesStore } from "@/stores/objectStoreInstancesStore";
import _l from "@/utils/localization";

import InstanceDropdown from "./InstanceDropdown.vue";
import ManageIndexHeader from "@/components/ConfigTemplates/ManageIndexHeader.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";
import ObjectStoreTypeSpan from "@/components/ObjectStore/ObjectStoreTypeSpan.vue";
import TemplateSummarySpan from "@/components/ObjectStore/Templates/TemplateSummarySpan.vue";

const objectStoreInstancesStore = useObjectStoreInstancesStore();

interface Props {
    message: String | undefined | null;
}

defineProps<Props>();

const BADGE_FIELD = {
    key: "badges",
    label: _l(" "),
    sortable: false,
};

const fields = [NAME_FIELD, DESCRIPTION_FIELD, TYPE_FIELD, TEMPLATE_FIELD, BADGE_FIELD];

const allItems = computed<UserConcreteObjectStore[]>(() => objectStoreInstancesStore.getInstances);
const { activeInstances } = useFiltering(allItems);
const loading = computed(() => objectStoreInstancesStore.loading);
objectStoreInstancesStore.fetchInstances();

function reload() {
    objectStoreInstancesStore.fetchInstances();
}
</script>

<template>
    <div>
        <ManageIndexHeader
            :message="message"
            create-button-id="object-store-create"
            create-route="/object_store_instances/create">
        </ManageIndexHeader>
        <BTable
            id="user-object-stores-index"
            no-sort-reset
            :fields="fields"
            :items="activeInstances"
            :hover="true"
            :striped="true"
            :caption-top="true"
            :fixed="true"
            :show-empty="true">
            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="Loading storage location instances" />
                <b-alert v-else id="no-object-store-instances" variant="info" show>
                    <div>No storage location instances found, click the create button to configure a new one.</div>
                </b-alert>
            </template>
            <template v-slot:cell(badges)="row">
                <ObjectStoreBadges size="1x" :badges="row.item.badges" />
            </template>
            <template v-slot:cell(name)="row">
                <InstanceDropdown :object-store="row.item" @entryRemoved="reload" />
            </template>
            <template v-slot:cell(type)="row">
                <ObjectStoreTypeSpan :type="row.item.type" />
            </template>
            <template v-slot:cell(template)="row">
                <TemplateSummarySpan
                    :template-version="row.item.template_version ?? 0"
                    :template-id="row.item.template_id" />
            </template>
        </BTable>
    </div>
</template>
