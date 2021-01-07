import jQuery from "jquery";
import { getGalaxyInstance } from "app";
import UI_MODAL from "mvc/ui/ui-modal";
import _l from "utils/localization";
import Vue from "vue";

function collectionCreatorModalSetup(options) {
    const deferred = jQuery.Deferred();
    const Galaxy = getGalaxyInstance();
    const modal = Galaxy.modal || new UI_MODAL.View();
    options.oncancel = function () {
        modal.hide();
        deferred.reject("cancelled");
    };
    options.oncreate = function (creator, response) {
        modal.hide();
        deferred.resolve(response);
    };
    const showEl = function (el) {
        modal.show({
            title: options.title || _l("Create a collection"),
            body: el,
            width: "85%",
            height: "100%",
            xlarge: true,
            closing_events: true,
        });
    };
    return { deferred, showEl };
}

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
    const { deferred, creatorOptions, showEl } = collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
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
            return deferred;
        }
    );
}
function createCollectionViaRules(selection, defaultHideSourceItems) {
    let elements;
    let elementsType;
    let importType;
    const selectionType = selection.selectionType;
    const copyElements = !defaultHideSourceItems;
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
        const hasNonWhitespaceChars = RegExp(/[^\s]/);
        // Have pasted data, data from a history dataset, or FTP list.
        const lines = selection.content
            .split(/[\n\r]/)
            .filter((line) => line.length > 0 && hasNonWhitespaceChars.exec(line));
        // Really poor tabular parser - we should get a library for this or expose options? I'm not
        // sure.
        let hasTabs = false;
        if (lines.length > 0) {
            const firstLine = lines[0];
            if (firstLine.indexOf("\t") >= 0) {
                hasTabs = true;
            }
        }
        const regex = hasTabs ? /\t/ : /\s+/;
        elements = lines.map((line) => line.split(regex));
        elementsType = selection.selectionType;
        importType = selection.dataType || "collections";
    }
    const promise = ruleBasedCollectionCreatorModal(elements, elementsType, importType, {
        ftpUploadSite: selection.ftpUploadSite,
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function (elements, collectionType, name, hideSourceItems) {
            return selection.createHDCA(elements, collectionType, name, hideSourceItems, copyElements);
        },
    });
    return promise;
}

export default {
    ruleBasedCollectionCreatorModal: ruleBasedCollectionCreatorModal,
    createCollectionViaRules: createCollectionViaRules,
};
