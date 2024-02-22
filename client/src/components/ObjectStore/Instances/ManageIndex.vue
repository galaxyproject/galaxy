<script setup lang="ts">
import "./icons";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useObjectStoreInstancesStore } from "@/stores/objectStoreInstancesStore";
import _l from "@/utils/localization";

import InstanceDropdown from "./InstanceDropdown.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";
import ObjectStoreTypeSpan from "@/components/ObjectStore/ObjectStoreTypeSpan.vue";
import TemplateSummarySpan from "@/components/ObjectStore/Templates/TemplateSummarySpan.vue";

const router = useRouter();
const objectStoreInstancesStore = useObjectStoreInstancesStore();

interface Props {
    message: String | undefined | null;
}

defineProps<Props>();

const fields = [
    {
        key: "name",
        label: _l("Name"),
        sortable: true,
    },
    {
        key: "description",
        label: _l("Description"),
        sortable: true,
    },
    {
        key: "type",
        label: _l("Type"),
        sortable: true,
    },
    {
        key: "template",
        label: _l("From Template"),
        sortable: true,
    },
    {
        key: "badges",
        label: _l(" "),
        sortable: false,
    },
];

const items = computed(() => objectStoreInstancesStore.getInstances);
const loading = computed(() => objectStoreInstancesStore.loading);
objectStoreInstancesStore.fetchInstances();
</script>

<template>
    <div>
        <p>
            {{ message || "" }}
        </p>
        <b-row class="mb-3">
            <b-col>
                <b-button
                    id="object-store-create"
                    class="m-1 float-right"
                    @click="router.push('/object_store_instances/create')">
                    <FontAwesomeIcon icon="plus" />
                    {{ _l("Create") }}
                </b-button>
            </b-col>
        </b-row>
        <b-table
            no-sort-reset
            :fields="fields"
            :items="items"
            :hover="true"
            :striped="true"
            :caption-top="true"
            :fixed="true"
            :show-empty="true">
            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="Loading object store instances" />
                <b-alert v-else id="no-object-store-instances" variant="info" show>
                    <div>No object store instances found, click the create button to configure a new one.</div>
                </b-alert>
            </template>
            <template v-slot:cell(badges)="row">
                <ObjectStoreBadges size="1x" :badges="row.item.badges" />
            </template>
            <template v-slot:cell(name)="row">
                <InstanceDropdown :object-store="row.item" />
            </template>
            <template v-slot:cell(type)="row">
                <ObjectStoreTypeSpan :type="row.item.type" />
            </template>
            <template v-slot:cell(template)="row">
                <TemplateSummarySpan
                    :template-version="row.item.template_version ?? 0"
                    :template-id="row.item.template_id" />
            </template>
        </b-table>
    </div>
</template>
