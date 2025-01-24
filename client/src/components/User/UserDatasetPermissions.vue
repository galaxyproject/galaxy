<script lang="ts" setup>
import axios from "axios";
import { computed, ref } from "vue";

import { initRefs, updateRefs, useCallbacks } from "@/composables/datasetPermissions";
import { withPrefix } from "@/utils/redirect";

import DatasetPermissionsForm from "@/components/Dataset/DatasetPermissionsForm.vue";

interface UserDatasetPermissionsProps {
    userId: string;
}
const props = defineProps<UserDatasetPermissionsProps>();

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
    return `/api/users/${props.userId}/permissions/inputs`;
});

async function init() {
    const { data } = await axios.get(withPrefix(inputsUrl.value));
    updateRefs(data.inputs, managePermissionsOptions, accessPermissionsOptions, managePermissions, accessPermissions);
    loading.value = false;
}

const title = "Set Dataset Permissions for New Histories";

const formConfig = computed(() => {
    return {
        title: title,
        id: "edit-preferences-permissions",
        description:
            "Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored.",
        url: inputsUrl.value,
        icon: "fa-users",
        submitTitle: "Save Permissions",
        redirect: "/user",
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
