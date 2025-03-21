<script setup lang="ts">
import "ui/hoverhighlight";

import { faSquare } from "@fortawesome/free-regular-svg-icons";
import { faMinus, faSortAlphaDown, faTimes, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup } from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";

import type { HDASummary, HistoryItemSummary } from "@/api";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import STATES from "@/mvc/dataset/states";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import localize from "@/utils/localization";

import FormSelectMany from "../Form/Elements/FormSelectMany/FormSelectMany.vue";
import HelpText from "../Help/HelpText.vue";
import CollectionCreator from "@/components/Collections/common/CollectionCreator.vue";
import DatasetCollectionElementView from "@/components/Collections/ListDatasetCollectionElementView.vue";

const NOT_VALID_ELEMENT_MSG: string = localize("is not a valid element for this collection");

interface Props {
    historyId: string;
    initialElements: HistoryItemSummary[];
    defaultHideSourceItems?: boolean;
    suggestedName?: string;
    fromSelection?: boolean;
    extensions?: string[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "clicked-create", workingElements: HDASummary[], collectionName: string, hideSourceItems: boolean): void;
    (e: "on-cancel"): void;
}>();

const state = ref("build");
const duplicateNames = ref<string[]>([]);
const invalidElements = ref<string[]>([]);
const workingElements = ref<HDASummary[]>([]);
const selectedDatasetElements = ref<string[]>([]);
const hideSourceItems = ref(props.defaultHideSourceItems || false);
const atLeastOneElement = ref(true);

const atLeastOneDatasetIsSelected = computed(() => {
    return selectedDatasetElements.value.length > 0;
});
const getSelectedDatasetElements = computed(() => {
    return selectedDatasetElements.value;
});
const noMoreValidDatasets = computed(() => {
    return workingElements.value.length == 0;
});
const returnInvalidElementsLength = computed(() => {
    return invalidElements.value.length > 0;
});
const returnInvalidElements = computed(() => {
    return invalidElements.value;
});
const noInitialElements = computed(() => {
    return props.initialElements.length == 0;
});
const showDuplicateError = computed(() => {
    return duplicateNames.value.length > 0;
});
const allElementsAreInvalid = computed(() => {
    return props.initialElements.length == invalidElements.value.length;
});

/** If not `fromSelection`, the list of elements that will become the collection */
const inListElements = ref<HDASummary[]>([]);

// variables for datatype mapping and then filtering
const datatypesMapperStore = useDatatypesMapperStore();
const datatypesMapper = computed(() => datatypesMapperStore.datatypesMapper);

/** Are we filtering by datatype? */
const filterExtensions = computed(() => !!datatypesMapper.value && !!props.extensions?.length);

/** Does `inListElements` have elements with different extensions? */
const listHasMixedExtensions = computed(() => {
    const extensions = new Set(inListElements.value.map((e) => e.extension));
    return extensions.size > 1;
});

// ----------------------------------------------------------------------- process raw list
/** set up main data */
function _elementsSetUp() {
    /** a list of invalid elements and the reasons they aren't valid */
    invalidElements.value = [];

    //TODO: handle fundamental problem of syncing DOM, views, and list here
    /** data for list in progress */
    workingElements.value = [];

    // copy initial list, sort, add ids if needed
    workingElements.value = JSON.parse(JSON.stringify(props.initialElements.slice(0)));

    // reverse the order of the elements to emulate what we have in the history panel
    workingElements.value.reverse();

    // for inListElements, reset their values (in order) to datasets from workingElements
    const inListElementsPrev = inListElements.value;
    inListElements.value = [];
    inListElementsPrev.forEach((prevElem) => {
        const element = workingElements.value.find((e) => e.id === prevElem.id);
        const problem = _isElementInvalid(prevElem);

        if (element) {
            inListElements.value.push(element);
        } else if (problem) {
            const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${problem} 和 ${NOT_VALID_ELEMENT_MSG}`;
            invalidElements.value.push(invalidMsg);
            Toast.error(invalidMsg, localize("无效的元素"));
        } else {
            const invalidMsg = `${prevElem.hid}: ${prevElem.name} ${localize("已从集合中移除")}`;
            invalidElements.value.push(invalidMsg);
            Toast.error(invalidMsg, localize("无效的元素"));
        }
    });

    // _ensureElementIds();
    _validateElements();
    _mangleDuplicateNames();
}

// TODO: not sure if this is needed
// function _ensureElementIds() {
//     workingElements.value.forEach((element) => {
//         if (!Object.prototype.hasOwnProperty.call(element, "id")) {
//             console.warn("Element missing id", element);
//         }
//     });

//     return workingElements.value;
// }

// /** separate working list into valid and invalid elements for this collection */
function _validateElements() {
    workingElements.value = workingElements.value.filter((element) => {
        var problem = _isElementInvalid(element);

        if (problem) {
            invalidElements.value.push(element.name + "  " + problem);
        }

        return !problem;
    });

    return workingElements.value;
}

/** describe what is wrong with a particular element if anything */
function _isElementInvalid(element: HistoryItemSummary): string | null {
    if (element.history_content_type === "dataset_collection") {
        return localize("集合不允许这样操作");
    }

    var validState = element.state === STATES.OK || STATES.NOT_READY_STATES.includes(element.state as string);

    if (!validState) {
        return localize("发生错误, 处于已暂停或无法访问");
    }

    if (element.deleted || element.purged) {
        return localize("已被删除或清除");
    }

    if (
        filterExtensions.value &&
        element.extension &&
        !datatypesMapper.value?.isSubTypeOfAny(element.extension, props.extensions!)
    ) {
        return localize(`格式无效: ${element.extension}`);
    }
    return null;
}

/** Show the element's extension next to its name:
 *  1. If there are no required extensions, so users can avoid creating mixed extension lists.
 *  2. If the extension is not in the list of required extensions but is a subtype of one of them,
 *     so users can see that those elements were still included as they are implicitly convertible.
 */
function showElementExtension(element: HDASummary) {
    return (
        !props.extensions?.length ||
        (filterExtensions.value &&
            element.extension &&
            !props.extensions?.includes(element.extension) &&
            datatypesMapper.value?.isSubTypeOfAny(element.extension, props.extensions!))
    );
}

// /** mangle duplicate names using a mac-like '(counter)' addition to any duplicates */
function _mangleDuplicateNames() {
    var counter = 1;
    var existingNames: { [key: string]: boolean } = {};

    workingElements.value.forEach((element) => {
        var currName = element.name;

        while (Object.prototype.hasOwnProperty.call(existingNames, currName as string)) {
            currName = `${element.name} (${counter})`;
            counter += 1;
        }

        element.name = currName;
        existingNames[element.name as string] = true;
    });
}

function changeDatatypeFilter(newFilter: "all" | "datatype" | "ext") {
    _elementsSetUp();
}

function elementSelected(e: HDASummary) {
    if (!selectedDatasetElements.value.includes(e.id)) {
        selectedDatasetElements.value.push(e.id);
    } else {
        selectedDatasetElements.value.splice(selectedDatasetElements.value.indexOf(e.id), 1);
    }
}

function elementDiscarded(e: HDASummary) {
    workingElements.value.splice(workingElements.value.indexOf(e), 1);
    selectedDatasetElements.value = selectedDatasetElements.value.filter((element) => {
        return element !== e.id;
    });

    return workingElements.value;
}

function clickClearAll() {
    selectedDatasetElements.value = [];
}

function clickRemoveSelected() {
    workingElements.value = workingElements.value.filter((element) => {
        return !selectedDatasetElements.value.includes(element.id);
    });

    selectedDatasetElements.value = [];
}

function clickSelectAll() {
    selectedDatasetElements.value = workingElements.value.map((element) => {
        return element.id;
    });
}
const { confirm } = useConfirmDialog();

async function clickedCreate(collectionName: string) {
    checkForDuplicates();

    const returnedElements = props.fromSelection ? workingElements.value : inListElements.value;
    atLeastOneElement.value = returnedElements.length > 0;

    let confirmed = false;
    if (!atLeastOneElement.value) {
        confirmed = await confirm(localize("您确定要创建一个没有数据集的列表吗？"), {
            title: localize("创建一个空列表"),
            okTitle: localize("创建"),
            okVariant: "primary",
        });
    }

    if (state.value !== "error" && (atLeastOneElement.value || confirmed)) {
        emit("clicked-create", returnedElements, collectionName, hideSourceItems.value);
    }
}

function checkForDuplicates() {
    var valid = true;
    var existingNames: { [key: string]: boolean } = {};

    duplicateNames.value = [];

    workingElements.value.forEach((element) => {
        if (Object.prototype.hasOwnProperty.call(existingNames, element.name as string)) {
            valid = false;
            duplicateNames.value.push(element.name as string);
        }

        existingNames[element.name as string] = true;
    });

    state.value = valid ? "build" : "error";
}

/** reset all data to the initial state */
function reset() {
    /** Ids of elements that have been selected by the user - to preserve over renders */
    selectedDatasetElements.value = [];
    _elementsSetUp();
}

function sortByName() {
    workingElements.value.sort(compareNames);
}

function compareNames(a: HDASummary, b: HDASummary) {
    if (a.name && b.name && a.name < b.name) {
        return -1;
    }
    if (a.name && b.name && a.name > b.name) {
        return 1;
    }

    return 0;
}

function onUpdateHideSourceItems(newHideSourceItems: boolean) {
    hideSourceItems.value = newHideSourceItems;
}

watch(
    () => props.initialElements,
    () => {
        // for any new/removed elements, add them to working elements
        _elementsSetUp();
    },
    { immediate: true }
);

watch(
    () => datatypesMapper.value,
    async (mapper) => {
        if (props.extensions?.length && !mapper) {
            await datatypesMapperStore.createMapper();
        }
    },
    { immediate: true }
);

function addUploadedFiles(files: HDASummary[]) {
    const returnedElements = props.fromSelection ? workingElements : inListElements;
    files.forEach((f) => {
        const file = props.fromSelection ? f : workingElements.value.find((e) => e.id === f.id);
        const problem = _isElementInvalid(f);
        if (file && !returnedElements.value.find((e) => e.id === file.id)) {
            returnedElements.value.push(file);
        } else if (problem) {
            invalidElements.value.push("上传的项: " + f.name + "  " + problem);
            Toast.error(
                localize(`数据集 ${f.hid}: ${f.name} ${problem}，这是一个无效元素，无法添加到此集合`),
                localize("上传的项无效")
            );
        } else {
            invalidElements.value.push("上传的项: " + f.name + " 无法添加到集合");
            Toast.error(
                localize(`数据集 ${f.hid}: ${f.name} 无法添加到集合`),
                localize("上传的项无效")
            );
        }
    });
}

/** find the element in the workingElements array and update its name */
function renameElement(element: any, name: string) {
    element = workingElements.value.find((e) => e.id === element.id);
    if (element) {
        element.name = name;
    }
}

function selectionAsHdaSummary(value: any): HDASummary {
    return value as HDASummary;
}

//TODO: issue #9497
// const removeExtensions = ref(true);
// removeExtensionsToggle: function () {
//     this.removeExtensions = !this.removeExtensions;
//     if (this.removeExtensions == true) {
//         this.removeExtensionsFn();
//     }
// },
// removeExtensionsFn: function () {
//     workingElements.value.forEach((e) => {
//         var lastDotIndex = e.lastIndexOf(".");
//         if (lastDotIndex > 0) {
//             var extension = e.slice(lastDotIndex, e.length);
//             e = e.replace(extension, "");
//         }
//     });
// },
</script>

<template>
    <div class="list-collection-creator">
        <div v-if="!showDuplicateError && state == 'error'">
            <BAlert show variant="danger">
                {{ localize("创建集合时出现问题。") }}
            </BAlert>
        </div>
        <div v-else>
            <div v-if="fromSelection && returnInvalidElementsLength">
                <BAlert show variant="warning" dismissible>
                    {{ localize("以下选择因下列原因无法包含：") }}
                    <ul>
                        <li v-for="problem in returnInvalidElements" :key="problem">
                            {{ problem }}
                        </li>
                    </ul>
                </BAlert>
            </div>

            <div v-if="!atLeastOneElement">
                <BAlert show variant="warning" dismissible @dismissed="atLeastOneElement = true">
                    {{ localize("至少需要一个元素来创建列表。") }}
                    <span v-if="fromSelection">
                        <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                            {{ localize("取消") }}
                        </a>
                        {{ localize("并重新选择新元素。") }}
                    </span>
                </BAlert>
            </div>

            <div v-if="showDuplicateError">
                <BAlert show variant="danger">
                    {{
                        localize("集合不能有重复的名称。以下列表名称是重复的：")
                    }}
                    <ol>
                        <li v-for="name in duplicateNames" :key="name">{{ name }}</li>
                    </ol>
                    {{ localize("请修复这些重复项并重试。") }}
                </BAlert>
            </div>

            <CollectionCreator
                :oncancel="() => emit('on-cancel')"
                :history-id="props.historyId"
                :hide-source-items="hideSourceItems"
                :extensions="extensions"
                collection-type="list"
                :no-items="props.initialElements.length == 0 && !props.fromSelection"
                :show-upload="!fromSelection"
                :suggested-name="props.suggestedName"
                @add-uploaded-files="addUploadedFiles"
                @on-update-datatype-toggle="changeDatatypeFilter"
                @onUpdateHideSourceItems="onUpdateHideSourceItems"
                @clicked-create="clickedCreate">
                <template v-slot:help-content>
                    <p>
                        {{
                            localize(
                                [
                                    "此界面允许您创建一个新的 Galaxy 数据集列表。",
                                    "列表是 Galaxy 数据集集合的一种类型，是一个永久的、有序的数据集列表，可以传递给工具",
                                    "和工作流，以便对整个组的每个成员进行分析。此界面允许",
                                    "您创建和重新排序数据集列表。Galaxy 集合中的数据集有一个标识符，该标识符在",
                                    "工具执行过程中保留，并作为样本追踪的形式 - 设置此名称将为该元素",
                                    "列表中的标识符，但不会更改数据集在 Galaxy 中的实际名称。",
                                ].join("")
                            )
                        }}
                    </p>

                    <ul>
                        <li v-if="!fromSelection">
                            将数据集从“未选择”列移动到下面的“已选择”列，以按照预期顺序和数据集组成列表。
                        </li>
                        <li v-if="!fromSelection">
                            可以使用过滤框快速按名称查找感兴趣的数据集。
                        </li>
                        <li>
                            {{ localize("通过点击") }}
                            <i data-target=".collection-element .name">
                                {{ localize("现有名称") }}
                            </i>
                            {{ localize("来更改列表中元素的标识符。") }}
                        </li>

                        <li>
                            {{ localize("通过点击") }}
                            <i v-if="fromSelection" data-target=".collection-element .discard">
                                {{ localize("删除") }}
                            </i>
                            <i v-else data-target=".collection-element .discard">
                                {{ localize("丢弃") }}
                            </i>
                            {{ localize("按钮从最终创建的列表中删除元素。") }}
                        </li>

                        <li v-if="fromSelection">
                            {{
                                localize(
                                    "通过点击和拖动元素来重新排序列表。点击它们以选择多个元素"
                                )
                            }}
                            <i data-target=".collection-element">
                                {{ localize("它们") }}
                            </i>
                            {{
                                localize(
                                    "，然后您可以通过拖动整个组来移动选中的元素。再次点击或点击"
                                )
                            }}
                            <i data-target=".clear-selected">
                                {{ localize("清除选中项") }}
                            </i>
                            {{ localize("来取消选择。") }}
                        </li>

                        <li v-if="fromSelection">
                            {{ localize("点击") }}
                            <i data-target=".reset">
                                <FontAwesomeIcon :icon="faUndo" />
                            </i>
                            {{ localize("重新开始，就像刚刚打开界面一样。") }}
                        </li>

                        <li v-if="fromSelection">
                            {{ localize("点击") }}
                            <i data-target=".sort-items">
                                <FontAwesomeIcon :icon="faSortAlphaDown" />
                            </i>
                            {{ localize("按字母顺序对数据集进行排序。") }}
                        </li>

                        <li>
                            {{ localize("点击") }}
                            <i data-target=".cancel-create">
                                {{ localize("取消") }}
                            </i>
                            {{ localize("按钮退出界面。") }}
                        </li>
                    </ul>

                    <br />

                    <p>
                        {{ localize("一旦您的集合完成，请输入一个") }}
                        <i data-target=".collection-name">
                            {{ localize("名称") }}
                        </i>
                        {{ localize("并点击") }}
                        <i data-target=".create-collection">
                            {{ localize("创建列表") }}
                        </i>
                        {{ localize("。") }}
                    </p>
                </template>

                <template v-slot:middle-content>
                    <BAlert v-if="listHasMixedExtensions" show variant="warning" dismissible>
                        {{ localize("所选数据集格式混合。") }}
                        {{ localize("您仍然可以创建列表，但通常来说") }}
                        {{ localize("数据集列表应包含相同类型的数据集。") }}
                        <HelpText
                            uri="galaxy.collections.collectionBuilder.whyHomogenousCollections"
                            :text="localize('为什么？')" />
                    </BAlert>
                    <div v-if="noInitialElements">
                        <BAlert show variant="warning" dismissible>
                            {{ localize("未选择任何数据集") }}
                            {{ localize("至少需要一个元素用于集合。您可能需要") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("取消") }}
                            </a>
                            {{ localize("并重新选择新元素，或上传数据集。") }}
                        </BAlert>
                    </div>
                    <div v-else-if="allElementsAreInvalid">
                        <BAlert v-if="!fromSelection" show variant="warning">
                            {{
                                localize(
                                    "您的历史记录中没有有效的元素用于此列表。\
                                    您可能需要切换到不同的历史记录或上传有效的数据集。"
                                )
                            }}
                            <div v-if="extensions?.length">
                                {{ localize("此列表所需的格式如下：") }}
                                <ul>
                                    <li v-for="extension in extensions" :key="extension">
                                        {{ extension }}
                                    </li>
                                </ul>
                            </div>
                        </BAlert>
                        <BAlert v-else show variant="warning" dismissible>
                            {{ localize("以下选择因问题无法包含：") }}
                            <ul>
                                <li v-for="problem in returnInvalidElements" :key="problem">
                                    {{ problem }}
                                </li>
                            </ul>
                            {{ localize("至少需要一个元素用于集合。您可能需要") }}
                            <a class="cancel-text" href="javascript:void(0)" role="button" @click="emit('on-cancel')">
                                {{ localize("取消") }}
                            </a>
                            {{ localize("并重新选择新元素，或上传有效的数据集。") }}
                        </BAlert>
                    </div>
                    <div v-else-if="fromSelection">
                        <div class="collection-elements-controls">
                            <div>
                                <BButton
                                    class="reset"
                                    :title="localize('重置为初始状态')"
                                    size="sm"
                                    @click="reset">
                                    <FontAwesomeIcon :icon="faUndo" fixed-width />
                                    {{ localize("重置") }}
                                </BButton>
                                <BButton
                                    class="sort-items"
                                    :title="localize('按名称排序数据集')"
                                    size="sm"
                                    @click="sortByName">
                                    <FontAwesomeIcon :icon="faSortAlphaDown" />
                                </BButton>
                            </div>

                            <div class="center-text">
                                <u>{{ workingElements.length }}</u> {{ localize("列表中的元素") }}
                            </div>

                            <div>
                                <span v-if="atLeastOneDatasetIsSelected"
                                    >{{ localize("选择的数据集") }} ({{ selectedDatasetElements.length }}):</span
                                >
                                <BButtonGroup class="" size="sm">
                                    <BButton
                                        v-if="atLeastOneDatasetIsSelected"
                                        :title="localize('从列表中删除选中的数据集')"
                                        @click="clickRemoveSelected">
                                        <FontAwesomeIcon :icon="faMinus" fixed-width />
                                        {{ localize("删除") }}
                                    </BButton>
                                    <BButton
                                        v-if="
                                            !atLeastOneDatasetIsSelected ||
                                            selectedDatasetElements.length < workingElements.length
                                        "
                                        :title="localize('选择所有数据集')"
                                        size="sm"
                                        @click="clickSelectAll">
                                        <FontAwesomeIcon :icon="faSquare" fixed-width />
                                        {{ localize("选择所有") }}
                                    </BButton>
                                    <BButton
                                        v-if="atLeastOneDatasetIsSelected"
                                        class="clear-selected"
                                        :title="localize('取消选择所有选中的数据集')"
                                        @click="clickClearAll">
                                        <FontAwesomeIcon :icon="faTimes" fixed-width />
                                        {{ localize("清除") }}
                                    </BButton>
                                </BButtonGroup>
                            </div>
                        </div>

                        <div v-if="noMoreValidDatasets">
                            <BAlert show variant="warning">
                                {{ localize("没有剩余的有效元素。您是否希望") }}
                                <a class="reset-text" href="javascript:void(0)" role="button" @click="reset">
                                    {{ localize("重新开始") }}
                                </a>
                                ?
                            </BAlert>
                        </div>

                        <draggable
                            v-model="workingElements"
                            class="collection-elements scroll-container flex-row drop-zone"
                            chosen-class="bg-secondary">
                            <DatasetCollectionElementView
                                v-for="element in workingElements"
                                :key="element.id"
                                :class="{ selected: getSelectedDatasetElements.includes(element.id) }"
                                :element="element"
                                has-actions
                                :selected="getSelectedDatasetElements.includes(element.id)"
                                @element-is-selected="elementSelected"
                                @element-is-discarded="elementDiscarded"
                                @onRename="(name) => (element.name = name)" />
                        </draggable>
                    </div>

                    <FormSelectMany
                        v-else
                        v-model="inListElements"
                        maintain-selection-order
                        :placeholder="localize('按名称筛选数据集')"
                        :options="workingElements.map((e) => ({ label: e.name || '', value: e }))">
                        <template v-slot:label-area="{ value }">
                            <DatasetCollectionElementView
                                class="w-100"
                                :element="selectionAsHdaSummary(value)"
                                :hide-extension="!showElementExtension(selectionAsHdaSummary(value))"
                                @onRename="(name) => renameElement(value, name)" />
                        </template>
                    </FormSelectMany>
                </template>
            </CollectionCreator>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "base.scss";
@import "theme/blue.scss";

.list-collection-creator {
    .footer {
        margin-top: 8px;
    }

    .cancel-create {
        border-color: lightgrey;
    }

    .collection-elements-controls {
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;

        .center-text {
            position: absolute;
            transform: translateX(-50%);
            left: 50%;
        }
    }

    .collection-elements {
        max-height: 400px;
        border: 0px solid lightgrey;
        overflow-y: auto;
        overflow-x: hidden;
    }

    // TODO: taken from .dataset above - swap these out
    .collection-element {
        height: 32px;
        opacity: 1;
        padding: 0 8px 0 8px;
        line-height: 28px;
        cursor: pointer;
        overflow: hidden;
        border: 1px solid lightgrey;
        border-radius: 3px;

        &.with-actions {
            margin: 2px 4px 0px 4px;
            &:hover {
                border-color: black;
            }
        }
        &:not(.with-actions) {
            &:hover {
                border: none;
            }
        }

        &:last-of-type {
            margin-bottom: 2px;
        }

        &.selected {
            border-color: black;
            background: rgb(118, 119, 131);
            color: white;
            a {
                color: white;
            }
        }
    }

    .empty-message {
        margin: 8px;
        color: grey;
        font-style: italic;
        text-align: center;
    }
}
</style>
