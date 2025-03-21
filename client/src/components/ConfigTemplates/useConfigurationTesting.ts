import { computed, type Ref, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type Instance, type PluginStatus, type TemplateSummary } from "@/api/configTemplates";
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

type CreateTestUrl = "/api/object_store_instances/test" | "/api/file_source_instances/test";
type CreateUrl = "/api/object_store_instances" | "/api/file_source_instances";

export function useConfigurationTemplateCreation<T extends TemplateSummary, R>(
    what: string, 
    template: Ref<T>, 
    uuid: Ref<string | undefined>, 
    testUrl: CreateTestUrl, 
    createUrl: CreateUrl, 
    onCreate: (result: R) => unknown
) {
    const error = ref<string | null>(null);
    const { testRunning, testResults } = useConfigurationTesting();

    async function onSubmit(formData: any) {
        const payload = createFormDataToPayload(template.value, formData);
        if (uuid.value) {
            payload.uuid = uuid.value;
        }
        let pluginStatus: PluginStatus;
        try {
            testRunning.value = true;
            const { data, error: testRequestError } = await GalaxyApi().POST(testUrl, {
                body: payload,
            });
            if (testRequestError) {
                error.value = "验证配置失败: " + errorMessageAsString(testRequestError);
                return;
            } else {
                pluginStatus = data;
                testResults.value = pluginStatus;
            }
        } catch (e) {
            error.value = "验证配置失败: " + errorMessageAsString(e);
            return;
        } finally {
            testRunning.value = false;
        }
        if (pluginStatus) {
            const testError = pluginStatusToErrorMessage(pluginStatus);
            if (testError) {
                error.value = testError;
                return;
            }
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
        return createTemplateForm(template.value, what);
    });

    const submitTitle = "创建";
    const loadingMessage = `加载 ${what} 模板和实例信息`;

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

export function useConfigurationTemplateEdit<T extends TemplateSummary, R extends Instance>(
    what: string,
    instance: Ref<R | null>,
    template: Ref<T | null>,
    testUpdateUrl: TestUpdateUrl,
    updateUrl: UpdateUrl,
    useRouting: InstanceRoutingComposableType
) {
    const { testRunning, testResults } = useConfigurationTesting();
    const showForceActionButton = ref<boolean>(false);

    const { goToIndex } = useRouting();

    async function onUpdate(objectStore: R) {
        const message = `${what} ${objectStore.name} 已更新`;
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
    const submitTitle = "更新设置";
    const loadingMessage = `加载 ${what} 模板和实例信息`;

    async function onSubmit(formData: any) {
        if (template.value && instance.value) {
            const payload = editFormDataToPayload(template.value, formData);

            let pluginStatus;
            try {
                testRunning.value = true;
                showForceActionButton.value = false;
                const { data: pluginStatus, error: testRequestError } = await GalaxyApi().POST(testUpdateUrl, {
                    params: { path: { uuid: instance.value.uuid } },
                    body: payload,
                });
                if (testRequestError) {
                    error.value = errorMessageAsString(testRequestError);
                    showForceActionButton.value = true;
                }
                testResults.value = pluginStatus;
            } catch (e) {
                error.value = errorMessageAsString(e);
                showForceActionButton.value = true;
                return;
            } finally {
                testRunning.value = false;
            }
            if (pluginStatus) {
                const testError = pluginStatusToErrorMessage(pluginStatus);
                if (testError) {
                    error.value = testError;
                    showForceActionButton.value = true;
                    return;
                }
            }

            try {
                const { data, error: updateRequestError } = await GalaxyApi().PUT(updateUrl, {
                    params: { path: { uuid: instance.value.uuid } },
                    body: payload,
                });
                if (updateRequestError) {
                    error.value = errorMessageAsString(updateRequestError);
                } else {
                    await onUpdate(data as R);
                }
            } catch (e) {
                error.value = errorMessageAsString(e);
                return;
            }
        }
    }

    async function onForceSubmit(formData: any) {
        if (template.value && instance.value) {
            const payload = editFormDataToPayload(template.value, formData);
            try {
                const { data, error: updateRequestError } = await GalaxyApi().PUT(updateUrl, {
                    params: { path: { uuid: instance.value.uuid } },
                    body: payload,
                });
                if (updateRequestError) {
                    error.value = errorMessageAsString(updateRequestError);
                } else {
                    await onUpdate(data as R);
                }
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
    testUpdateUrl: TestUpdateUrl,
    updateUrl: UpdateUrl,
    useRouting: InstanceRoutingComposableType
) {
    const { goToIndex } = useRouting();

    async function onUpgrade(objectStore: R) {
        const message = `${what} ${objectStore.name} 已升级`;
        goToIndex({ message });
    }

    const error = ref<string | null>(null);
    const { testRunning, testResults } = useConfigurationTesting();
    const showForceActionButton = ref<boolean>(false);

    const submitTitle = "升级配置";
    const loadingMessage = `加载最新的 ${what} 模板和实例信息`;

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

        const payload = upgradeFormDataToPayload(template.value, formData);
        let pluginStatus;
        try {
            testRunning.value = true;
            showForceActionButton.value = false;
            const { data: pluginStatus, error: testRequestError } = await GalaxyApi().POST(testUpdateUrl, {
                params: { path: { uuid: instance.value.uuid } },
                body: payload,
            });
            if (testRequestError) {
                error.value = errorMessageAsString(testRequestError);
                showForceActionButton.value = true;
                return;
            } else {
                testResults.value = pluginStatus;
            }
        } catch (e) {
            showForceActionButton.value = true;
            error.value = errorMessageAsString(e);
            return;
        } finally {
            testRunning.value = false;
        }
        if (pluginStatus) {
            const testError = pluginStatusToErrorMessage(pluginStatus);
            if (testError) {
                error.value = testError;
                showForceActionButton.value = true;
                return;
            }
        }
        try {
            const { data, error: updateRequestError } = await GalaxyApi().PUT(updateUrl, {
                params: { path: { uuid: instance.value.uuid } },
                body: payload,
            });
            if (updateRequestError) {
                error.value = errorMessageAsString(updateRequestError);
            } else {
                await onUpgrade(data as R);
            }
        } catch (e) {
            error.value = errorMessageAsString(e);
            return;
        }
    }

    async function onForceSubmit(formData: any) {
        const payload = upgradeFormDataToPayload(template.value, formData);
        try {
            const { data, error: updateRequestError } = await GalaxyApi().PUT(updateUrl, {
                params: { path: { uuid: instance.value.uuid } },
                body: payload,
            });
            if (updateRequestError) {
                error.value = errorMessageAsString(updateRequestError);
            } else {
                await onUpgrade(data as R);
            }
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