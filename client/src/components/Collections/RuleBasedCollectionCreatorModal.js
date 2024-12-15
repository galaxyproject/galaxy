import _l from "utils/localization";
import Vue from "vue";

import { rawToTable } from "@/components/Collections/tables";

import { collectionCreatorModalSetup } from "./common/modal";

function ruleBasedCollectionCreatorModal(elements, elementsType, importType, options) {
    // importType in [datasets, collection]
    // elementsType in [raw, ftp, datasets]
    let title;
    if (importType == "datasets") {
        title = _l("Build Rules for Uploading Datasets");
    } else if (elementsType == "collection_contents") {
        title = _l("Build Rules for Applying to Existing Collection");
    } else if (elementsType == "datasets" || elementsType == "library_datasets") {
        title = _l("Build Rules for Creating Collection(s)");
    } else {
        title = _l("Build Rules for Uploading Collections");
    }
    options.title = title;
    // Prevents user from accidentally closing the modal by clicking outside the bounds
    options.closing_events = false;
    const { promise, showEl } = collectionCreatorModalSetup(options);
    return import(/* webpackChunkName: "ruleCollectionBuilder" */ "components/RuleCollectionBuilder.vue").then(
        (module) => {
            var ruleCollectionBuilderInstance = Vue.extend(module.default);
            var vm = document.createElement("div");
            showEl(vm);
            new ruleCollectionBuilderInstance({
                propsData: {
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
            }).$mount(vm);
            return promise;
        }
    );
}
function createCollectionViaRules(selection, defaultHideSourceItems = true) {
    let elements;
    let elementsType;
    let importType;
    const selectionType = selection.selectionType;
    if (!selectionType) {
        // Have HDAs from the history panel.
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
    const promise = ruleBasedCollectionCreatorModal(elements, elementsType, importType, {
        ftpUploadSite: selection.ftpUploadSite,
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function (elements, collectionType, name, hideSourceItems) {
            return selection.createHDCA(elements, collectionType, name, hideSourceItems);
        },
    });
    return promise;
}

export default {
    ruleBasedCollectionCreatorModal: ruleBasedCollectionCreatorModal,
    createCollectionViaRules: createCollectionViaRules,
};
