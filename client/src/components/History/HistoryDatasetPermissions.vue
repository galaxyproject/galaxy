<script lang="ts" setup>
import axios from "axios";
import { computed, ref } from "vue";

import { initRefs, updateRefs, useCallbacks } from "@/composables/datasetPermissions";
import { withPrefix } from "@/utils/redirect";

import DatasetPermissionsForm from "@/components/Dataset/DatasetPermissionsForm.vue";

interface HistoryDatasetPermissionsProps {
    historyId: string;
}
const props = defineProps<HistoryDatasetPermissionsProps>();

const loading = ref(true);

const {
    managePermissionsOptions,
    accessPermissionsOptions,
    managePermissions,
    accessPermissions,
    simplePermissions,
    checked,
} = initRefs();

const inputsUrl = computed(() => {
    return `/history/permissions?id=${props.historyId}`;
});

const title = "Change default dataset permissions for history";

const formConfig = computed(() => {
    return {
        title: title,
        url: inputsUrl.value,
        submitTitle: "Save Permissions",
        redirect: "/histories/list",
    };
});

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
    axios.put(withPrefix(inputsUrl.value), formValue).then(onSuccess).catch(onError);
}

async function init() {
    const { data } = await axios.get(withPrefix(inputsUrl.value));
    updateRefs(data.inputs, managePermissionsOptions, accessPermissionsOptions, managePermissions, accessPermissions);
    loading.value = false;
}

const { onSuccess, onError } = useCallbacks(init);
</script>

<template>
    <DatasetPermissionsForm
        :loading="loading"
        :simple-permissions="simplePermissions"
        :title="title"
        :form-config="formConfig"
        :checked="checked"
        @change="change" />
</template>
