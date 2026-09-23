import { computed, type ComputedRef } from "vue";

import type { UploadOptionVisibility } from "@/components/Panels/Upload/shared/uploadOptionVisibility";
import type { BulkUploadItem, BulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import {
    isUploadOptionVisible,
    uploadOptionDefinitions,
    type UploadOptionKey,
} from "@/composables/upload/uploadOptionModel";

type HeaderOptionProps = {
    options: HeaderOptionDescriptor[];
};

type HeaderOptionEvents = {
    toggle: (key: UploadOptionKey) => void;
};

type RowOptionProps = {
    options: RowOptionDescriptor[];
};

type RowOptionEvents = {
    update: (payload: { key: UploadOptionKey; value: boolean }) => void;
};

export interface HeaderOptionDescriptor {
    key: UploadOptionKey;
    label: string;
    title: string;
    checked: boolean;
    indeterminate: boolean;
}

export interface RowOptionDescriptor {
    key: UploadOptionKey;
    label: string;
    title: string;
    checked: boolean;
}

type BulkOptionState = {
    checked: boolean;
    indeterminate: boolean;
};

type OptionAdapter<T extends BulkUploadItem> = {
    isSupported: (item: T) => boolean;
    get: (item: T) => boolean;
    set: (item: T, value: boolean) => void;
    getBulkState: (bulk: BulkUploadOperations) => BulkOptionState;
    toggleBulk: (bulk: BulkUploadOperations) => void;
};

const optionAdapters: Record<UploadOptionKey, OptionAdapter<BulkUploadItem>> = {
    spaceToTab: {
        isSupported: () => true,
        get: (item) => item.spaceToTab,
        set: (item, value) => {
            item.spaceToTab = value;
        },
        getBulkState: (bulk) => ({
            checked: bulk.allSpaceToTab.value,
            indeterminate: bulk.spaceToTabIndeterminate.value,
        }),
        toggleBulk: (bulk) => {
            bulk.toggleAllSpaceToTab();
        },
    },
    toPosixLines: {
        isSupported: () => true,
        get: (item) => item.toPosixLines,
        set: (item, value) => {
            item.toPosixLines = value;
        },
        getBulkState: (bulk) => ({
            checked: bulk.allToPosixLines.value,
            indeterminate: bulk.toPosixLinesIndeterminate.value,
        }),
        toggleBulk: (bulk) => {
            bulk.toggleAllToPosixLines();
        },
    },
    autoDecompress: {
        isSupported: () => true,
        get: (item) => item.autoDecompress,
        set: (item, value) => {
            item.autoDecompress = value;
        },
        getBulkState: (bulk) => ({
            checked: bulk.allAutoDecompress.value,
            indeterminate: bulk.autoDecompressIndeterminate.value,
        }),
        toggleBulk: (bulk) => {
            bulk.toggleAllAutoDecompress();
        },
    },
    deferred: {
        isSupported: (item) => "deferred" in item,
        get: (item) => item.deferred ?? false,
        set: (item, value) => {
            if ("deferred" in item) {
                item.deferred = value;
            }
        },
        getBulkState: (bulk) => ({
            checked: bulk.allDeferred.value,
            indeterminate: bulk.deferredIndeterminate.value,
        }),
        toggleBulk: (bulk) => {
            bulk.toggleAllDeferred();
        },
    },
};

export function useUploadOptionBindings<T extends BulkUploadItem>(
    bulk: BulkUploadOperations,
    optionVisibility: ComputedRef<UploadOptionVisibility>,
) {
    const headerOptions = computed<HeaderOptionDescriptor[]>(() => {
        const visibility = optionVisibility.value;

        return uploadOptionDefinitions
            .filter((definition) => isUploadOptionVisible(definition.key, visibility))
            .map((definition) => {
                const state = optionAdapters[definition.key].getBulkState(bulk);

                return {
                    key: definition.key,
                    label: definition.label,
                    title: definition.headerTooltip,
                    checked: state.checked,
                    indeterminate: state.indeterminate,
                };
            });
    });

    const headerOptionProps = computed<HeaderOptionProps>(() => {
        return {
            options: headerOptions.value,
        };
    });

    const headerOptionEvents = computed<HeaderOptionEvents>(() => {
        return {
            toggle: (key: UploadOptionKey) => {
                optionAdapters[key].toggleBulk(bulk);
            },
        };
    });

    function getRowOptionProps(item: T): RowOptionProps {
        const visibility = optionVisibility.value;

        return {
            options: uploadOptionDefinitions
                .filter((definition) => isUploadOptionVisible(definition.key, visibility))
                .filter((definition) => optionAdapters[definition.key].isSupported(item))
                .map((definition) => ({
                    key: definition.key,
                    label: definition.label,
                    title: definition.rowTooltip,
                    checked: optionAdapters[definition.key].get(item),
                })),
        };
    }

    function getRowOptionEvents(item: T): RowOptionEvents {
        return {
            update: ({ key, value }: { key: UploadOptionKey; value: boolean }) => {
                optionAdapters[key].set(item, value);
            },
        };
    }

    return {
        headerOptionProps,
        headerOptionEvents,
        getRowOptionProps,
        getRowOptionEvents,
    };
}
