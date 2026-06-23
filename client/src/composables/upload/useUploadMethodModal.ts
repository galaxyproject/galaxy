import Vue, { h, reactive } from "vue";

import type { DataOption } from "@/components/Form/Elements/FormData/types";
import type {
    DatasetUploadMethod,
    UploadedDataset,
    UploadModalConfig,
    UploadModalResolvers,
    UploadModalResult,
} from "@/components/Panels/Upload/uploadModalTypes";

import UploadMethodModal from "@/components/Panels/Upload/UploadMethodModal.vue";

interface ModalState {
    modalVisible: boolean;
    modalConfig: UploadModalConfig;
}

interface UploadMethodModalHostInstance extends Vue {
    state: ModalState;
    render: () => ReturnType<typeof h>;
}

const DEFAULT_ALLOWED_METHODS: DatasetUploadMethod[] = [
    "local-file",
    "paste-content",
    "paste-links",
    "remote-files",
    "data-library",
];

let hostElement: HTMLDivElement | null = null;
let modalVm: UploadMethodModalHostInstance | null = null;
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

function ensureMounted(): UploadMethodModalHostInstance {
    if (modalVm) {
        return modalVm;
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

    const render = () =>
        h(UploadMethodModal, {
            props: {
                show: state.modalVisible,
                config: state.modalConfig,
                hideTips: state.modalConfig.hideTips ?? false,
            },
            on: {
                "update:show": (show: boolean) => {
                    state.modalVisible = show;
                },
                uploaded: finishUploaded,
                cancelled: finishCancelled,
            },
        });

    const instance = new Vue({
        name: "UploadMethodModalHost",
        setup() {
            return {
                state,
                finishUploaded,
                finishCancelled,
                render,
            };
        },
        render(): ReturnType<typeof h> {
            return this.render();
        },
    }).$mount(hostElement);

    modalVm = instance as UploadMethodModalHostInstance;
    return modalVm;
}

export function useUploadMethodModal() {
    async function openUploadModal(config?: UploadModalConfig): Promise<UploadModalResult> {
        const vm = ensureMounted();

        if (pendingResolvers) {
            return Promise.reject(new Error("An upload modal is already open."));
        }

        const defaultedConfig = applyConfigDefaults(config);
        vm.state.modalConfig = defaultedConfig;
        vm.state.modalVisible = true;

        return new Promise<UploadModalResult>((resolve, reject) => {
            pendingResolvers = { resolve, reject };
        });
    }

    return {
        openUploadModal,
    };
}

export { toDataOptions };
