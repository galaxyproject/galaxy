import { computed, type Ref, ref } from "vue";

import type {
    CreateInstancePayload,
    Instance,
    PluginStatus,
    TemplateSummary,
    TestUpdateInstancePayload,
    TestUpgradeInstancePayload,
    UpdateInstancePayload,
    UpgradeInstancePayload,
} from "@/api/configTemplates";
import { type buildInstanceRoutingComposable } from "@/components/ConfigTemplates/routing";
import { errorMessageAsString } from "@/utils/simple-error";

import {
    createFormDataToPayload,
    createTemplateForm,
    editFormDataToPayload,
    editTemplateForm,
    type FormEntry,
    pluginStatusToErrorMessage,
    upgradeForm,
    upgradeFormDataToPayload,
} from "./formUtil";

import ActionSummary from "./ActionSummary.vue";
import ConfigurationTestSummaryModal from "@/components/ConfigTemplates/ConfigurationTestSummaryModal.vue";
import InstanceForm from "@/components/ConfigTemplates/InstanceForm.vue";

type InstanceRoutingComposableType = ReturnType<typeof buildInstanceRoutingComposable>;

export function useConfigurationTesting() {
    const testRunning = ref<boolean>(false);
    const testResults = ref<PluginStatus | undefined>(undefined);

    return {
        testRunning,
        testResults,
    };
}

export function useConfigurationTemplateCreation<T extends TemplateSummary, R>(
    what: string,
    template: Ref<T>,
    uuid: Ref<string | undefined>,
    test: (payload: CreateInstancePayload) => Promise<{ data: PluginStatus }>,
    create: (payload: CreateInstancePayload) => Promise<{ data: R }>,
    onCreate: (result: R) => unknown
) {
    const error = ref<string | null>(null);
    const { testRunning, testResults } = useConfigurationTesting();

    async function onSubmit(formData: any) {
        const payload = createFormDataToPayload(template.value, formData);
        if (uuid.value) {
            payload.uuid = uuid.value;
        }
        let pluginStatus;
        try {
            testRunning.value = true;
            const response = await test(payload);
            pluginStatus = response["data"];
            testResults.value = pluginStatus;
        } catch (e) {
            error.value = "Failed to verify configuration: " + errorMessageAsString(e);
            return;
        } finally {
            testRunning.value = false;
        }
        const testError = pluginStatusToErrorMessage(pluginStatus);
        if (testError) {
            error.value = testError;
            return;
        }
        try {
            const { data: userObject } = await create(payload);
            onCreate(userObject);
        } catch (e) {
            error.value = errorMessageAsString(e);
            return;
        }
    }

    const inputs = computed<FormEntry[]>(() => {
        return createTemplateForm(template.value, what);
    });

    const submitTitle = "Create";
    const loadingMessage = `Loading ${what} template and instance information`;

    return {
        ActionSummary,
        error,
        inputs,
        InstanceForm,
        onSubmit,
        submitTitle,
        loadingMessage,
        testRunning,
        testResults,
    };
}

export function useInstanceTesting<R extends Instance>(testInstance: (id: string) => Promise<{ data: PluginStatus }>) {
    const showTestResults = ref(false);
    const testResults = ref<PluginStatus | undefined>(undefined);
    const testingError = ref<string | undefined>(undefined);

    async function test(instance: R) {
        testResults.value = undefined;
        testingError.value = undefined;
        showTestResults.value = true;
        try {
            const { data } = await testInstance(instance.uuid);
            testResults.value = data;
        } catch (e) {
            testingError.value = errorMessageAsString(e);
        }
    }

    return {
        ConfigurationTestSummaryModal,
        showTestResults,
        testResults,
        testingError,
        test,
    };
}

export function useConfigurationTemplateEdit<T extends TemplateSummary, R extends Instance>(
    what: string,
    instance: Ref<R | null>,
    template: Ref<T | null>,
    testUpdate: (payload: TestUpdateInstancePayload) => Promise<{ data: PluginStatus }>,
    update: (payload: UpdateInstancePayload) => Promise<{ data: R }>,
    useRouting: InstanceRoutingComposableType
) {
    const { testRunning, testResults } = useConfigurationTesting();
    const showForceActionButton = ref<boolean>(false);

    const { goToIndex } = useRouting();

    async function onUpdate(objectStore: R) {
        const message = `Updated ${what} ${objectStore.name}`;
        goToIndex({ message });
    }

    const inputs = computed<Array<FormEntry> | undefined>(() => {
        const realizedInstance = instance.value;
        const realizedTemplate = template.value;
        if (!realizedInstance || !realizedTemplate) {
            return undefined;
        }
        return editTemplateForm(realizedTemplate, what, realizedInstance);
    });

    const error = ref<string | null>(null);
    const hasSecrets = computed(() => instance.value?.secrets && instance.value?.secrets.length > 0);
    const submitTitle = "Update Settings";
    const loadingMessage = `Loading ${what} template and instance information`;

    async function onSubmit(formData: any) {
        if (template.value) {
            const payload = editFormDataToPayload(template.value, formData);

            let pluginStatus;
            try {
                testRunning.value = true;
                showForceActionButton.value = false;
                const response = await testUpdate(payload);
                pluginStatus = response["data"];
                testResults.value = pluginStatus;
            } catch (e) {
                error.value = errorMessageAsString(e);
                showForceActionButton.value = true;
                return;
            } finally {
                testRunning.value = false;
            }
            const testError = pluginStatusToErrorMessage(pluginStatus);
            if (testError) {
                error.value = testError;
                showForceActionButton.value = true;
                return;
            }

            try {
                const response = await update(payload);
                await onUpdate(response["data"]);
            } catch (e) {
                error.value = errorMessageAsString(e);
                return;
            }
        }
    }

    async function onForceSubmit(formData: any) {
        if (template.value) {
            const payload = editFormDataToPayload(template.value, formData);
            try {
                const response = await update(payload);
                await onUpdate(response["data"]);
            } catch (e) {
                error.value = errorMessageAsString(e);
                return;
            }
        }
    }

    return {
        error,
        ActionSummary,
        inputs,
        InstanceForm,
        hasSecrets,
        loadingMessage,
        onForceSubmit,
        onSubmit,
        showForceActionButton,
        submitTitle,
        testResults,
        testRunning,
    };
}

export function useConfigurationTemplateUpgrade<T extends TemplateSummary, R extends Instance>(
    what: string,
    instance: Ref<R>,
    template: Ref<T>,
    testUpdate: (payload: TestUpgradeInstancePayload) => Promise<{ data: PluginStatus }>,
    update: (payload: UpgradeInstancePayload) => Promise<{ data: R }>,
    useRouting: InstanceRoutingComposableType
) {
    const { goToIndex } = useRouting();

    async function onUpgrade(objectStore: R) {
        const message = `Upgraded ${what} ${objectStore.name}`;
        goToIndex({ message });
    }

    const error = ref<string | null>(null);
    const { testRunning, testResults } = useConfigurationTesting();
    const showForceActionButton = ref<boolean>(false);

    const submitTitle = "Upgrade Configuration";
    const loadingMessage = `Loading latest ${what} template and instance information`;

    const inputs = computed<Array<FormEntry> | undefined>(() => {
        const realizedInstance = instance.value;
        const realizedLatestTemplate = template.value;
        if (!realizedInstance || !realizedLatestTemplate) {
            return undefined;
        }
        const form = upgradeForm(realizedLatestTemplate, realizedInstance);
        return form;
    });

    async function onSubmit(formData: any) {
        const payload = upgradeFormDataToPayload(template.value, formData);
        let pluginStatus;
        try {
            testRunning.value = true;
            showForceActionButton.value = false;
            const response = await testUpdate(payload);
            pluginStatus = response["data"];
            testResults.value = pluginStatus;
        } catch (e) {
            showForceActionButton.value = true;
            error.value = errorMessageAsString(e);
            return;
        } finally {
            testRunning.value = false;
        }
        const testError = pluginStatusToErrorMessage(pluginStatus);
        if (testError) {
            error.value = testError;
            showForceActionButton.value = true;
            return;
        }

        try {
            const response = await update(payload);
            await onUpgrade(response["data"]);
        } catch (e) {
            error.value = errorMessageAsString(e);
            return;
        }
    }

    async function onForceSubmit(formData: any) {
        const payload = upgradeFormDataToPayload(template.value, formData);
        try {
            const response = await update(payload);
            await onUpgrade(response["data"]);
        } catch (e) {
            error.value = errorMessageAsString(e);
            return;
        }
    }

    return {
        error,
        ActionSummary,
        inputs,
        InstanceForm,
        loadingMessage,
        onForceSubmit,
        onSubmit,
        submitTitle,
        showForceActionButton,
        testResults,
        testRunning,
    };
}
