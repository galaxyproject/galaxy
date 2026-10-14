import { computed, type Ref, ref } from "vue";

import { GalaxyApi } from "@/api";
import type { Instance, PluginStatus, TemplateSummary } from "@/api/configTemplates";
import type { buildInstanceRoutingComposable } from "@/components/ConfigTemplates/routing";
import { errorMessageAsString } from "@/utils/simple-error";

import {
    createFormDataToPayload,
    createTemplateForm,
    type DynamicOptions,
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

type TestRequest = () => Promise<{ data?: PluginStatus; error?: unknown }>;

export function useConfigurationTesting() {
    const testRunning = ref<boolean>(false);
    const testResults = ref<PluginStatus | undefined>(undefined);

    /**
     * Run a configuration test and record its results. Returns why saving should stop,
     * or undefined when the configuration checks out.
     */
    async function runTest(request: TestRequest, requestErrorPrefix = ""): Promise<string | undefined> {
        testRunning.value = true;
        try {
            const { data, error } = await request();
            if (error) {
                return requestErrorPrefix + errorMessageAsString(error);
            }
            testResults.value = data;
            return (data && pluginStatusToErrorMessage(data)) || undefined;
        } catch (e) {
            return requestErrorPrefix + errorMessageAsString(e);
        } finally {
            testRunning.value = false;
        }
    }

    return {
        testRunning,
        testResults,
        runTest,
    };
}

type CreateTestUrl = "/api/object_store_instances/test" | "/api/file_source_instances/test";
type CreateUrl = "/api/object_store_instances" | "/api/file_source_instances";

export function useConfigurationTemplateCreation<T extends TemplateSummary, R>(
    what: string,
    template: Ref<T>,
    uuid: Ref<string | undefined>,
    testUrl: CreateTestUrl,
    createUrl: CreateUrl,
    onCreate: (result: R) => unknown,
    dynamicOptions?: Ref<DynamicOptions>,
) {
    const error = ref<string | null>(null);
    const { testRunning, testResults, runTest } = useConfigurationTesting();

    async function onSubmit(formData: any) {
        const payload = createFormDataToPayload(template.value, formData);
        if (uuid.value) {
            payload.uuid = uuid.value;
        }
        const testError = await runTest(
            () => GalaxyApi().POST(testUrl, { body: payload }),
            "Failed to verify configuration: ",
        );
        if (testError) {
            error.value = testError;
            return;
        }
        try {
            const { data: userObject, error: createRequestError } = await GalaxyApi().POST(createUrl, {
                body: payload,
            });
            if (createRequestError) {
                error.value = errorMessageAsString(createRequestError);
            } else {
                onCreate(userObject as R);
            }
        } catch (e) {
            error.value = errorMessageAsString(e);
            return;
        }
    }

    const inputs = computed<FormEntry[]>(() => {
        return createTemplateForm(template.value, what, dynamicOptions?.value);
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

type TestInstanceUrl = "/api/file_source_instances/{uuid}/test" | "/api/object_store_instances/{uuid}/test";

export function useInstanceTesting<R extends Instance>(testUrl: TestInstanceUrl) {
    const showTestResults = ref(false);
    const testResults = ref<PluginStatus | undefined>(undefined);
    const testingError = ref<string | undefined>(undefined);

    async function test(instance: R) {
        testResults.value = undefined;
        testingError.value = undefined;
        showTestResults.value = true;
        try {
            const { data, error } = await GalaxyApi().GET(testUrl, {
                params: { path: { uuid: instance.uuid } },
            });
            const pluginStatus = data;
            const testRequestError = error;
            if (testRequestError) {
                testingError.value = errorMessageAsString(testRequestError);
            } else {
                testResults.value = pluginStatus;
            }
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

type TestUpdateUrl = "/api/object_store_instances/{uuid}/test" | "/api/file_source_instances/{uuid}/test";
type UpdateUrl = "/api/object_store_instances/{uuid}" | "/api/file_source_instances/{uuid}";
type UpdatePayload = ReturnType<typeof editFormDataToPayload> | ReturnType<typeof upgradeFormDataToPayload>;

/** The test-then-save flow edit and upgrade share, with a force option when the test fails. */
function useTestThenUpdate<R extends Instance>(
    testUpdateUrl: TestUpdateUrl,
    updateUrl: UpdateUrl,
    onSaved: (result: R) => unknown,
) {
    const error = ref<string | null>(null);
    const showForceActionButton = ref<boolean>(false);
    const { testRunning, testResults, runTest } = useConfigurationTesting();

    async function update(uuid: string, payload: UpdatePayload) {
        try {
            const { data, error: updateRequestError } = await GalaxyApi().PUT(updateUrl, {
                params: { path: { uuid } },
                body: payload,
            });
            if (updateRequestError) {
                error.value = errorMessageAsString(updateRequestError);
            } else {
                await onSaved(data as R);
            }
        } catch (e) {
            error.value = errorMessageAsString(e);
        }
    }

    async function testThenUpdate(uuid: string, payload: UpdatePayload) {
        showForceActionButton.value = false;
        const testError = await runTest(() =>
            GalaxyApi().POST(testUpdateUrl, { params: { path: { uuid } }, body: payload }),
        );
        if (testError) {
            error.value = testError;
            showForceActionButton.value = true;
            return;
        }
        await update(uuid, payload);
    }

    return { error, showForceActionButton, testRunning, testResults, testThenUpdate, update };
}

export function useConfigurationTemplateEdit<T extends TemplateSummary, R extends Instance>(
    what: string,
    instance: Ref<R | null>,
    template: Ref<T | null>,
    testUpdateUrl: TestUpdateUrl,
    updateUrl: UpdateUrl,
    useRouting: InstanceRoutingComposableType,
    /**
     * Callback to be called when the object store is updated.
     * By default, no action is taken.
     */
    onUpdated: (result: R) => void = (__: R) => {},
) {
    const { goToIndex } = useRouting();

    function onUpdate(objectStore: R) {
        onUpdated(objectStore);
        const message = `Updated ${what} ${objectStore.name}`;
        goToIndex({ message });
    }

    const { error, showForceActionButton, testRunning, testResults, testThenUpdate, update } = useTestThenUpdate<R>(
        testUpdateUrl,
        updateUrl,
        onUpdate,
    );

    const inputs = computed<Array<FormEntry> | undefined>(() => {
        const realizedInstance = instance.value;
        const realizedTemplate = template.value;
        if (!realizedInstance || !realizedTemplate) {
            return undefined;
        }
        return editTemplateForm(realizedTemplate, what, realizedInstance);
    });

    const hasSecrets = computed(() => instance.value?.secrets && instance.value?.secrets.length > 0);
    const submitTitle = "Update Settings";
    const loadingMessage = `Loading ${what} template and instance information`;

    async function onSubmit(formData: any) {
        if (template.value && instance.value) {
            await testThenUpdate(instance.value.uuid, editFormDataToPayload(template.value, formData));
        }
    }

    async function onForceSubmit(formData: any) {
        if (template.value && instance.value) {
            await update(instance.value.uuid, editFormDataToPayload(template.value, formData));
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
    testUpdateUrl: TestUpdateUrl,
    updateUrl: UpdateUrl,
    useRouting: InstanceRoutingComposableType,
) {
    const { goToIndex } = useRouting();

    function onUpgrade(objectStore: R) {
        const message = `Upgraded ${what} ${objectStore.name}`;
        goToIndex({ message });
    }

    const { error, showForceActionButton, testRunning, testResults, testThenUpdate, update } = useTestThenUpdate<R>(
        testUpdateUrl,
        updateUrl,
        onUpgrade,
    );

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
        if (!instance.value || !template.value) {
            return;
        }
        await testThenUpdate(instance.value.uuid, upgradeFormDataToPayload(template.value, formData));
    }

    async function onForceSubmit(formData: any) {
        await update(instance.value.uuid, upgradeFormDataToPayload(template.value, formData));
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
