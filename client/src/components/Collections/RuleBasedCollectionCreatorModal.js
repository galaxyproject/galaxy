import { rawToTable } from "@/components/Collections/tables";
import _l from "@/utils/localization";
import Modal from "@/utils/modal";
import { mountVueComponent } from "@/utils/mountVueComponent";

const modal = new Modal();

async function ruleBasedCollectionCreatorModal(elements, elementsType, importType, options) {
    // importType in [datasets, collection]
    // elementsType in [raw, ftp, datasets]
    let title;
    if (importType === "datasets") {
        title = _l("Build Rules for Uploading Datasets");
    } else if (elementsType === "collection_contents") {
        title = _l("Build Rules for Applying to Existing Collection");
    } else if (elementsType === "datasets" || elementsType === "library_datasets") {
        title = _l("Build Rules for Creating Collection(s)");
    } else {
        title = _l("Build Rules for Uploading Collections");
    }

    const promise = new Promise((resolve, reject) => {
        options.oncancel = function () {
            modal.hide();
            resolve();
        };
        options.oncreate = function (response) {
            modal.hide();
            resolve(response);
        };
    });

    const module = await import("@/components/RuleCollectionBuilder.vue");
    const container = document.createElement("div");

    // Prepare modal
    const titleSuffix = options.historyName ? `From history: <b>${options.historyName}</b>` : "";
    const titleHtml = `<div class='d-flex justify-content-between unselectable'>
        <span>${title}</span>
        <span>${titleSuffix}</span>
    </div>`;
    modal.show({
        title: titleHtml,
        body: container,
        width: "85%",
        height: "100%",
    });

    // Mount rule builder component
    const mount = mountVueComponent(module.default);
    mount(
        {
            initialElements: elements,
            elementsType: elementsType,
            importType: importType,
            ftpUploadSite: options.ftpUploadSite,
            creationFn: options.creationFn,
            oncancel: options.oncancel,
            oncreate: options.oncreate,
            defaultHideSourceItems: options.defaultHideSourceItems,
            saveRulesFn: options.saveRulesFn,
            initialRules: options.initialRules,
        },
        container,
    );

    return promise;
}

export async function createCollectionViaRules(selection, defaultHideSourceItems = true) {
    let elements;
    let elementsType;
    let importType;
    const selectionType = selection.selectionType;
    if (!selectionType) {
        elements = selection.toJSON();
        elementsType = "datasets";
        importType = "collections";
    } else if (selection.elements) {
        elementsType = selection.selectionType;
        importType = selection.dataType || "collections";
        elements = selection.elements;
    } else {
        elements = rawToTable(selection.content);
        elementsType = selection.selectionType;
        importType = selection.dataType || "collections";
    }

    try {
        const result = await ruleBasedCollectionCreatorModal(elements, elementsType, importType, {
            ftpUploadSite: selection.ftpUploadSite,
            defaultHideSourceItems: defaultHideSourceItems,
            creationFn: async (elements, collectionType, name, hideSourceItems) => {
                return selection.createHDCA(elements, collectionType, name, hideSourceItems);
            },
        });
        return result;
    } catch (error) {
        console.error("Error in rule-based collection creation:", error);
        throw error;
    }
}
