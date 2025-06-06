import { computed, type Ref, ref, unref, watch } from "vue";

import type { CollectionElementIdentifiers, CreateNewCollectionPayload, HistoryItemSummary } from "@/api";
import type RuleCollectionBuilder from "@/components/RuleCollectionBuilder.vue";
import STATES from "@/mvc/dataset/states";
import localize from "@/utils/localization";

import type ListCollectionCreator from "./ListCollectionCreator.vue";
import type PairedOrUnpairedListCollectionCreator from "./PairedOrUnpairedListCollectionCreator.vue";
import { useCollectionCreation } from "./useCollectionCreation";
import { useExtensionFiltering } from "./useExtensionFilter";

export type Mode = "modal" | "wizard";

/** Terminal states that are not usable from an upload (anything but `ok` or `deferred`)
 */
const UNUSABLE_FROM_UPLOAD_STATES = Object.values(STATES.READY_STATES).filter(
    (state) => state !== STATES.OK && state !== STATES.DEFERRED
);

interface CommonCollectionBuilderProps {
    extensions?: string[];
    defaultHideSourceItems?: boolean;
    suggestedName?: string;
    mode: Mode;
}

type EmitsName = {
    (e: "name", value: string): void;
    (e: "input-valid", value: boolean): void;
    (e: "on-create", options: CreateNewCollectionPayload): void;
};

export type SupportedPairedOrPairedBuilderCollectionTypes =
    | "list:paired"
    | "list:paired_or_unpaired"
    | "list:list"
    | "list:list:paired";

export type CollectionCreatorComponent =
    | InstanceType<typeof ListCollectionCreator>
    | InstanceType<typeof PairedOrUnpairedListCollectionCreator>
    | InstanceType<typeof RuleCollectionBuilder>;

export async function attemptCreate(creator: CollectionCreatorComponent | Ref<CollectionCreatorComponent | undefined>) {
    const creatorValue: CollectionCreatorComponent | undefined = unref(creator);
    // fight typing to workaround https://github.com/vuejs/core/issues/10077
    interface HasAttemptCreate {
        attemptCreate: () => Promise<void>;
    }

    if (creatorValue) {
        (creatorValue as unknown as HasAttemptCreate).attemptCreate();
    }
}

export const showHid = true;

export function useCollectionCreator(props: CommonCollectionBuilderProps, emit?: EmitsName) {
    const removeExtensions = ref(true);
    const hideSourceItems = ref(props.defaultHideSourceItems || false);
    const collectionName = ref(props.suggestedName ?? "");

    const showButtonsForModal = computed(() => {
        return props.mode === "modal";
    });

    function onUpdateCollectionName(name: string) {
        collectionName.value = name;
    }

    const validInput = computed(() => !!collectionName.value);

    if (emit) {
        watch(collectionName, (newValue) => {
            console.log("name upated...");
            emit("name", newValue);
        });
        watch(validInput, (newValue) => {
            console.log("emitting...");
            emit("input-valid", newValue);
        });
    }

    const { hasInvalidExtension, showElementExtension } = useExtensionFiltering(props);
    const { createPayload } = useCollectionCreation();

    function onCollectionCreate(collectionType: string, elementIdentifiers: CollectionElementIdentifiers) {
        const payload = createPayload(collectionName.value, collectionType, elementIdentifiers, hideSourceItems.value);
        if (emit) {
            emit("on-create", payload);
        }
    }

    function onUpdateHideSourceItems(newHideSourceItems: boolean) {
        hideSourceItems.value = newHideSourceItems;
    }

    /** describe what is wrong with a particular element if anything */
    function isElementInvalid(element: HistoryItemSummary): string | null {
        if (element.history_content_type === "dataset_collection") {
            return localize("is a collection, this is not allowed");
        }

        if (UNUSABLE_FROM_UPLOAD_STATES.includes(element.state)) {
            return localize("has errored, is paused, or is not accessible");
        }

        if (element.deleted || element.purged) {
            return localize("has been deleted or purged");
        }

        // is the element's extension not a subtype of any of the required extensions?
        if (hasInvalidExtension(element)) {
            return localize(`has an invalid format: ${element.extension}`);
        }
        return null;
    }

    return {
        collectionName,
        removeExtensions,
        hideSourceItems,
        hasInvalidExtension,
        onUpdateHideSourceItems,
        isElementInvalid,
        showElementExtension,
        onUpdateCollectionName,
        validInput,
        onCollectionCreate,
        showButtonsForModal,
        showHid,
    };
}
