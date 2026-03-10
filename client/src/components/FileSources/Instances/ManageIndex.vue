<script setup lang="ts">
import { computed } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { DESCRIPTION_FIELD, NAME_FIELD, TEMPLATE_FIELD, TYPE_FIELD } from "@/components/ConfigTemplates/fields";
import { useInstanceTesting } from "@/components/ConfigTemplates/useConfigurationTesting";
import { useFiltering } from "@/components/ConfigTemplates/useInstanceFiltering";
import { useFileSourceInstancesStore } from "@/stores/fileSourceInstancesStore";

import GTable from "@/components/Common/GTable.vue";
import ManageIndexHeader from "@/components/ConfigTemplates/ManageIndexHeader.vue";
import FileSourceTypeSpan from "@/components/FileSources/FileSourceTypeSpan.vue";
import InstanceDropdown from "@/components/FileSources/Instances/InstanceDropdown.vue";
import TemplateSummarySpan from "@/components/FileSources/Templates/TemplateSummarySpan.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const fileSourceInstancesStore = useFileSourceInstancesStore();

interface Props {
    message?: string;
}

defineProps<Props>();

const fields: TableField[] = [NAME_FIELD, DESCRIPTION_FIELD, TYPE_FIELD, TEMPLATE_FIELD];

const allItems = computed(() => fileSourceInstancesStore.getInstances);
const { activeInstances } = useFiltering(allItems);
const loading = computed(() => fileSourceInstancesStore.loading);
fileSourceInstancesStore.fetchInstances();

function reload() {
    fileSourceInstancesStore.fetchInstances();
}

const testInstanceUrl = "/api/file_source_instances/{uuid}/test";

const { ConfigurationTestSummaryModal, showTestResults, testResults, test, testingError } =
    useInstanceTesting(testInstanceUrl);
</script>

<template>
    <div>
        <ConfigurationTestSummaryModal v-model="showTestResults" :error="testingError" :test-results="testResults" />
        <ManageIndexHeader header="My Repositories" :message="message" create-route="/file_source_instances/create">
        </ManageIndexHeader>

        <GTable
            id="user-file-sources-index"
            caption-top
            fixed
            hover
            show-empty
            striped
            :fields="fields"
            :items="activeInstances">
            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="Loading your user's file source instances" />
                <b-alert v-else id="no-file-source-instances" variant="info" show>
                    <div>
                        No file source instances found for your users, click the create button to configure a new one.
                    </div>
                </b-alert>
            </template>
            <template v-slot:cell(name)="{ item }">
                <InstanceDropdown :file-source="item" @entryRemoved="reload" @test="test(item)" />
            </template>
            <template v-slot:cell(type)="{ item }">
                <FileSourceTypeSpan :type="item.type" />
            </template>
            <template v-slot:cell(template)="{ item }">
                <TemplateSummarySpan :template-version="item.template_version ?? 0" :template-id="item.template_id" />
            </template>
        </GTable>
    </div>
</template>
