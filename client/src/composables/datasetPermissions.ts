import { type AxiosResponse } from "axios";
import { computed, type Ref, ref } from "vue";

import { useToast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

interface InputOption {
    roleName: string;
    roleValue: number;
}

export interface Input {
    value: number[];
    options: [string, number][];
}

export function initRefs() {
    const managePermissionsOptions = ref<InputOption[]>([]);
    const accessPermissionsOptions = ref<InputOption[]>([]);
    const managePermissions = ref<number[]>([]);
    const accessPermissions = ref<number[]>([]);

    const simplePermissions = computed(() => {
        // we have one manage permission and read access can be that or not that but nothing else
        const hasOneManagePermission = managePermissions.value.length == 1;
        const hasAtMostOneAccessPermissions = accessPermissions.value.length < 2;
        if (!hasOneManagePermission || !hasAtMostOneAccessPermissions) {
            return false;
        }
        const managePermissionValue = managePermissions.value[0];
        return accessPermissions.value.length == 0 || accessPermissions.value[0] == managePermissionValue;
    });

    const checked = computed(() => {
        return accessPermissions.value.length > 0;
    });

    return {
        managePermissionsOptions,
        accessPermissionsOptions,
        managePermissions,
        accessPermissions,
        simplePermissions,
        checked,
    };
}

export function permissionInputParts(inputs: Input[]) {
    const manageInput: Input = inputs[0] as Input;
    const accessInput: Input = inputs[1] as Input;
    return { manageInput, accessInput };
}

export function updateRefs(
    inputs: Input[],
    managePermissionsOptions: Ref<InputOption[]>,
    accessPermissionsOptions: Ref<InputOption[]>,
    managePermissions: Ref<number[]>,
    accessPermissions: Ref<number[]>
) {
    const { manageInput, accessInput } = permissionInputParts(inputs);
    managePermissionsOptions.value = manageInput.options.map((v: [string, number]) => {
        return <InputOption>{ roleName: v[0], roleValue: v[1] };
    });
    accessPermissionsOptions.value = accessInput.options.map((v: [string, number]) => {
        return <InputOption>{ roleName: v[0], roleValue: v[1] };
    });

    managePermissions.value = manageInput.value;
    accessPermissions.value = accessInput.value;
}

export function useCallbacks(init: () => void) {
    const toast = useToast();

    async function onError(e: unknown) {
        toast.error(errorMessageAsString(e));
    }

    async function onSuccess(data: AxiosResponse) {
        toast.success(data.data.message);
        init();
    }

    init();

    return { onSuccess, onError };
}
