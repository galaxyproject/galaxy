<script setup lang="ts">
import { BTable } from "bootstrap-vue";
import { computed } from "vue";

import { DESCRIPTION_FIELD, NAME_FIELD, TEMPLATE_FIELD, TYPE_FIELD } from "@/components/ConfigTemplates/fields";
import { useInstanceTesting } from "@/components/ConfigTemplates/useConfigurationTesting";
import { useFiltering } from "@/components/ConfigTemplates/useInstanceFiltering";
import { useFileSourceInstancesStore } from "@/stores/fileSourceInstancesStore";

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

const fields = [NAME_FIELD, DESCRIPTION_FIELD, TYPE_FIELD, TEMPLATE_FIELD];

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
        <ManageIndexHeader header="Remote File Sources" :message="message" create-route="/file_source_instances/create">
        </ManageIndexHeader>
        <BTable
            id="user-file-sources-index"
            no-sort-reset
            :fields="fields"
            :items="activeInstances"
            :hover="true"
            :striped="true"
            :caption-top="true"
            :fixed="true"
            :show-empty="true">
            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="Loading your user's file source instances" />
                <b-alert v-else id="no-file-source-instances" variant="info" show>
                    <div>
                        No file source instances found for your users, click the create button to configure a new one.
                    </div>
                </b-alert>
            </template>
            <template v-slot:cell(name)="row">
                <InstanceDropdown :file-source="row.item" @entryRemoved="reload" @test="test(row.item)" />
            </template>
            <template v-slot:cell(type)="row">
                <FileSourceTypeSpan :type="row.item.type" />
            </template>
            <template v-slot:cell(template)="row">
                <TemplateSummarySpan
                    :template-version="row.item.template_version ?? 0"
                    :template-id="row.item.template_id" />
            </template>
        </BTable>
    </div>
</template>
