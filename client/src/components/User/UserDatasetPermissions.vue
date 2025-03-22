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

const title = "为新历史记录设置数据集权限";

const formConfig = computed(() => {
    return {
        title: title,
        id: "edit-preferences-permissions",
        description:
            "为其他用户授予对新创建历史记录的默认访问权限。在这里所做的更改只会影响这些设置保存后创建的历史记录。",
        url: inputsUrl.value,
        icon: "fa-users",
        submitTitle: "保存权限",
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
