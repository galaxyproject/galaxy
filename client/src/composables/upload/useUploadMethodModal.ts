import { defineComponent, h, reactive } from "vue";

import type { DataOption } from "@/components/Form/Elements/FormData/types";
import type {
    DatasetUploadMethod,
    UploadedDataset,
    UploadModalConfig,
    UploadModalResolvers,
    UploadModalResult,
} from "@/components/Panels/Upload/uploadModalTypes";
import { mountVueComponent } from "@/utils/mountVueComponent";

import UploadMethodModal from "@/components/Panels/Upload/UploadMethodModal.vue";

interface ModalState {
    modalVisible: boolean;
    modalConfig: UploadModalConfig;
}

const DEFAULT_ALLOWED_METHODS: DatasetUploadMethod[] = [
    "local-file",
    "paste-content",
    "paste-links",
    "remote-files",
    "data-library",
];

export { DEFAULT_ALLOWED_METHODS };

let hostElement: HTMLDivElement | null = null;
let modalState: ModalState | null = null;
let pendingResolvers: UploadModalResolvers | null = null;

function toDataOptions(datasets: UploadedDataset[]): DataOption[] {
    return datasets.map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        hid: dataset.hid,
        src: dataset.src,
        batch: false,
        keep: true,
        tags: [],
    }));
}

function applyConfigDefaults(config?: UploadModalConfig): UploadModalConfig {
    return {
        allowedMethods: config?.allowedMethods ?? DEFAULT_ALLOWED_METHODS,
        allowCollections: config?.allowCollections ?? false,
        formats: config?.formats,
        multiple: config?.multiple ?? true,
        targetHistoryId: config?.targetHistoryId,
        title: config?.title,
        hideTips: config?.hideTips ?? false,
        immediateFiles: config?.immediateFiles,
    };
}

function buildResult(datasets: UploadedDataset[], cancelled: boolean): UploadModalResult {
    return {
        datasets,
        cancelled,
        toDataOptions: () => toDataOptions(datasets),
    };
}

function resolveAndCleanup(resolvers: UploadModalResolvers | null, result: UploadModalResult): void {
    if (resolvers) {
        resolvers.resolve(result);
    }
}

function ensureMounted(): ModalState {
    if (modalState) {
        return modalState;
    }

    hostElement = document.createElement("div");
    hostElement.id = "upload-method-modal-host";
    document.body.appendChild(hostElement);

    const state: ModalState = reactive({
        modalVisible: false,
        modalConfig: applyConfigDefaults(),
    });

    const finishUploaded = (datasets: UploadedDataset[]) => {
        const resolvers = pendingResolvers;
        pendingResolvers = null;
        state.modalVisible = false;
        resolveAndCleanup(resolvers, buildResult(datasets, false));
    };

    const finishCancelled = () => {
        const resolvers = pendingResolvers;
        pendingResolvers = null;
        state.modalVisible = false;
        resolveAndCleanup(resolvers, buildResult([], true));
    };

    const UploadMethodModalHost = defineComponent({
        name: "UploadMethodModalHost",
        setup() {
            return () =>
                h(UploadMethodModal, {
                    show: state.modalVisible,
                    config: state.modalConfig,
                    hideTips: state.modalConfig.hideTips ?? false,
                    "onUpdate:show": (show: boolean) => {
                        state.modalVisible = show;
                    },
                    onUploaded: finishUploaded,
                    onCancelled: finishCancelled,
                });
        },
    });

    // A separate app rather than a child of the main one, so it goes through the
    // shared helper to get the same pinia store and plugins.
    mountVueComponent(UploadMethodModalHost)({}, hostElement);

    modalState = state;
    return modalState;
}

export function useUploadMethodModal() {
    async function openUploadModal(config?: UploadModalConfig): Promise<UploadModalResult> {
        const state = ensureMounted();

        if (pendingResolvers) {
            return Promise.reject(new Error("An upload modal is already open."));
        }

        const defaultedConfig = applyConfigDefaults(config);
        state.modalConfig = defaultedConfig;
        state.modalVisible = true;

        return new Promise<UploadModalResult>((resolve, reject) => {
            pendingResolvers = { resolve, reject };
        });
    }

    return {
        openUploadModal,
    };
}

export { toDataOptions };
