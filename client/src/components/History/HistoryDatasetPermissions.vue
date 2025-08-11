<script lang="ts" setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

import { initRefs, updateRefs, useCallbacks } from "@/composables/datasetPermissions";
import { useHistoryBreadCrumbsToForProps } from "@/composables/historyBreadcrumbs";

import { getPermissions, getPermissionsUrl, setPermissions } from "./services";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import DatasetPermissionsForm from "@/components/Dataset/DatasetPermissionsForm.vue";

interface HistoryDatasetPermissionsProps {
    historyId: string;
    noRedirect?: boolean;
}
const props = defineProps<HistoryDatasetPermissionsProps>();

const route = useRoute();

const {
    managePermissionsOptions,
    accessPermissionsOptions,
    managePermissions,
    accessPermissions,
    simplePermissions,
    checked,
} = initRefs();

const inputsUrl = computed(() => {
    return getPermissionsUrl(props.historyId);
});

const title = "Change default dataset permissions for history";

const formConfig = computed(() => {
    return {
        title: title,
        url: inputsUrl.value,
        submitTitle: "Save Permissions",
        redirect: props.noRedirect ? undefined : "/histories/list",
    };
});

const { breadcrumbItems } = useHistoryBreadCrumbsToForProps(props, "Dataset Permissions");

async function change(value: unknown) {
    const managePermissionValue: number = managePermissions.value[0] as number;
    let access: number[] = [] as number[];
    if (value) {
        access = [managePermissionValue];
    }
    const formValue = {
        DATASET_MANAGE_PERMISSIONS: [managePermissionValue],
        DATASET_ACCESS: access,
    };
    setPermissions(props.historyId, formValue).then(onSuccess).catch(onError);
}

async function init() {
    const { data } = await getPermissions(props.historyId);
    updateRefs(data.inputs, managePermissionsOptions, accessPermissionsOptions, managePermissions, accessPermissions);
}

const { loading, loadError, onSuccess, onError } = useCallbacks(init);
</script>

<template>
    <div>
        <BreadcrumbHeading v-if="route.path === '/histories/permissions'" :items="breadcrumbItems" />

        <GAlert v-if="loadError" variant="danger">{{ loadError }}</GAlert>
        <DatasetPermissionsForm
            v-else
            :loading="loading"
            :simple-permissions="simplePermissions"
            :title="title"
            :form-config="formConfig"
            :checked="checked"
            @change="change" />
    </div>
</template>
