<template>
    <state-div v-if="state == 'build'">
        <!-- Different instructions if building up from individual datasets vs.
        initial data import.-->
        <rule-modal-header v-if="ruleView == 'source'"
            >Below is a raw JSON description of the rules to apply to the tabular data. This is an advanced
            setting.</rule-modal-header
        >
        <rule-modal-header v-else-if="elementsType == 'datasets' || elementsType == 'library_datasets'">
            Use this form to describe rules for building collection(s) from the specified datasets.
            <b>Be sure to specify at least one column as a list identifier</b> - specify more to created nested list
            structures. Specify a column to serve as "collection name" to group datasets into multiple collections.
        </rule-modal-header>
        <!-- This modality allows importing individual datasets, multiple collections,
        and requires a data source - note that.-->
        <rule-modal-header v-else-if="importType == 'datasets'">
            Use this form to describe rules for import datasets. At least one column should be defined to a source to
            fetch data from (URLs, FTP files, etc...).
        </rule-modal-header>
        <rule-modal-header v-else>
            Use this form to describe rules for import datasets. At least one column should be defined to a source to
            fetch data from (URLs, FTP files, etc...).
            <b>Be sure to specify at least one column as a list identifier</b> - specify more to created nested list
            structures. Specify a column to serve as "collection name" to group datasets into multiple collections.
        </rule-modal-header>
        <rule-modal-middle v-if="ruleView == 'source'">
            <p class="errormessagelarge" v-if="ruleSourceError">{{ ruleSourceError }}</p>
            <textarea class="rule-source" v-model="ruleSource"></textarea>
        </rule-modal-middle>
        <rule-modal-middle v-else>
            <!-- column-headers -->
            <div
                class="rule-builder-body vertically-spaced"
                :class="{ 'flex-column-container': vertical }"
                v-if="ruleView == 'normal'"
            >
                <!-- width: 30%; -->
                <div class="rule-column" :class="orientation">
                    <div
                        class="rules-container"
                        :class="{
                            'rules-container-vertical': initialElements && vertical,
                            'rules-container-horizontal': initialElements && horizontal,
                            'rules-container-full': initialElements == null,
                        }"
                    >
                        <rule-component rule-type="sort" :display-rule-type="displayRuleType" :builder="this">
                            <column-selector :target.sync="addSortingTarget" :col-headers="activeRuleColHeaders" />
                            <label v-b-tooltip.hover :title="titleNumericSort">
                                <input type="checkbox" v-model="addSortingNumeric" />
                                {{ l("Numeric sorting.") }}
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_column_basename"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector
                                :target.sync="addColumnBasenameTarget"
                                :col-headers="activeRuleColHeaders"
                            />
                        </rule-component>
                        <rule-component
                            rule-type="add_column_rownum"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <label>
                                {{ l("Starting from") }}
                                <input type="number" v-model="addColumnRownumStart" min="0" />
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_column_metadata"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <label>
                                {{ l("For") }}
                                <select v-model="addColumnMetadataValue">
                                    <!-- eslint-disable-next-line vue/require-v-for-key -->
                                    <option v-for="(col, index) in metadataOptions" :value="index">{{ col }}</option>
                                </select>
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_column_group_tag_value"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <label>
                                {{ l("Value") }}
                                <input type="text" v-model="addColumnGroupTagValueValue" />
                            </label>
                            <label>
                                {{ l("Default") }}
                                <input type="text" v-model="addColumnGroupTagValueDefault" />
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_column_regex"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector :target.sync="addColumnRegexTarget" :col-headers="activeRuleColHeaders" />
                            <label>
                                <input type="radio" v-model="addColumnRegexType" value="global" />Create column matching
                                expression.
                            </label>
                            <br />
                            <label>
                                <input type="radio" v-model="addColumnRegexType" value="groups" />Create columns
                                matching expression groups.
                            </label>
                            <br />
                            <label>
                                <input type="radio" v-model="addColumnRegexType" value="replacement" />Create column
                                from expression replacement.
                            </label>
                            <br />
                            <regular-expression-input :target.sync="addColumnRegexExpression" />
                            <label v-if="addColumnRegexType == 'groups'">
                                {{ l("Number of Groups") }}
                                <input type="number" v-model="addColumnRegexGroupCount" min="1" />
                            </label>
                            <label v-if="addColumnRegexType == 'replacement'">
                                {{ l("Replacement Expression") }}
                                <input type="text" v-model="addColumnRegexReplacement" class="rule-replacement" />
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_column_concatenate"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector
                                :target.sync="addColumnConcatenateTarget0"
                                :col-headers="activeRuleColHeaders"
                            />
                            <column-selector
                                :target.sync="addColumnConcatenateTarget1"
                                :col-headers="activeRuleColHeaders"
                            />
                        </rule-component>
                        <rule-component
                            rule-type="add_column_substr"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector :target.sync="addColumnSubstrTarget" :col-headers="activeRuleColHeaders" />
                            <label>
                                <select v-model="addColumnSubstrType">
                                    <option value="keep_prefix">Keep only prefix specified.</option>
                                    <option value="drop_prefix">Strip off prefix specified.</option>
                                    <option value="keep_suffix">Keep only suffix specified.</option>
                                    <option value="drop_suffix">Strip off suffix specified.</option>
                                </select>
                            </label>
                            <label>
                                {{ l("Prefix or suffix length") }}
                                <input type="number" v-model="addColumnSubstrLength" min="0" />
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_column_value"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <label>
                                {{ l("Value") }}
                                <input type="text" v-model="addColumnValue" />
                            </label>
                        </rule-component>
                        <rule-component rule-type="remove_columns" :display-rule-type="displayRuleType" :builder="this">
                            <column-selector
                                :target.sync="removeColumnTargets"
                                :col-headers="activeRuleColHeaders"
                                :multiple="true"
                            />
                        </rule-component>
                        <rule-component rule-type="split_columns" :display-rule-type="displayRuleType" :builder="this">
                            <column-selector
                                :target.sync="splitColumnsTargets0"
                                label="Odd Row Column(s)"
                                :col-headers="activeRuleColHeaders"
                                :multiple="true"
                            />
                            <column-selector
                                :target.sync="splitColumnsTargets1"
                                label="Even Row Column(s)"
                                :col-headers="activeRuleColHeaders"
                                :multiple="true"
                            />
                        </rule-component>
                        <rule-component rule-type="swap_columns" :display-rule-type="displayRuleType" :builder="this">
                            <column-selector
                                :target.sync="swapColumnsTarget0"
                                label="Swap Column"
                                :col-headers="activeRuleColHeaders"
                            />
                            <column-selector
                                :target.sync="swapColumnsTarget1"
                                label="With Column"
                                :col-headers="activeRuleColHeaders"
                            />
                        </rule-component>
                        <rule-component
                            rule-type="add_filter_regex"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector :target.sync="addFilterRegexTarget" :col-headers="activeRuleColHeaders" />
                            <regular-expression-input :target.sync="addFilterRegexExpression" />
                            <label v-b-tooltip.hover :title="titleInvertFilterRegex">
                                <input type="checkbox" v-model="addFilterRegexInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_filter_matches"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector
                                :target.sync="addFilterMatchesTarget"
                                :col-headers="activeRuleColHeaders"
                            />
                            <input type="text" v-model="addFilterMatchesValue" />
                            <label v-b-tooltip.hover :title="titleInvertFilterMatches">
                                <input type="checkbox" v-model="addFilterMatchesInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_filter_compare"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector
                                :target.sync="addFilterCompareTarget"
                                :col-headers="activeRuleColHeaders"
                            />
                            <label>
                                Filter out rows
                                <select v-model="addFilterCompareType">
                                    <option value="less_than">{{ l("less than") }}</option>
                                    <option value="less_than_equal">{{ l("less than or equal to") }}</option>
                                    <option value="greater_than">{{ l("greater than") }}</option>
                                    <option value="greater_than_equal">{{ l("greater than or equal to") }}</option>
                                </select>
                            </label>
                            <input type="text" v-model="addFilterCompareValue" />
                        </rule-component>
                        <rule-component
                            rule-type="add_filter_count"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <label>
                                Filter which rows?
                                <select v-model="addFilterCountWhich">
                                    <option value="first">first</option>
                                    <option value="last">last</option>
                                </select>
                            </label>
                            <label>
                                Filter how many rows?
                                <input type="number" v-model="addFilterCountN" />
                            </label>
                            <label v-b-tooltip.hover :title="titleInvertFilterMatches">
                                <input type="checkbox" v-model="addFilterCountInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <rule-component
                            rule-type="add_filter_empty"
                            :display-rule-type="displayRuleType"
                            :builder="this"
                        >
                            <column-selector :target.sync="addFilterEmptyTarget" :col-headers="activeRuleColHeaders" />
                            <label v-b-tooltip.hover :title="titleInvertFilterEmpty">
                                <input type="checkbox" v-model="addFilterEmptyInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <div v-if="displayRuleType == 'mapping'">
                            <div class="map" v-for="(map, index) in mapping" :index="index" :key="map.type">
                                <column-selector
                                    :class="'rule-map-' + map.type.replace(/_/g, '-')"
                                    :label="mappingTargets()[map.type].label"
                                    :help="mappingTargets()[map.type].help"
                                    :target.sync="map.columns"
                                    :ordered-edit.sync="map.editing"
                                    :col-headers="colHeaders"
                                    :multiple="mappingTargets()[map.type].multiple"
                                    :ordered="true"
                                    :value-as-list="true"
                                >
                                    <span
                                        v-b-tooltip.hover
                                        :title="titleRemoveMapping"
                                        class="fa fa-times"
                                        @click="removeMapping(index)"
                                    ></span>
                                </column-selector>
                            </div>
                            <div class="buttons rule-edit-buttons d-flex justify-content-end">
                                <button
                                    type="button"
                                    class="dropdown-toggle btn btn-primary mr-1"
                                    data-toggle="dropdown"
                                    v-if="unmappedTargets.length > 0"
                                >
                                    <span class="fa fa-plus rule-add-mapping"></span>
                                    {{ "Add Definition" }}
                                    <span class="caret"></span>
                                </button>
                                <div class="dropdown-menu" role="menu">
                                    <a
                                        v-for="target in unmappedTargets"
                                        :index="target"
                                        :key="target"
                                        class="dropdown-item"
                                        href="javascript:void(0)"
                                        :class="'rule-add-mapping-' + target.replace(/_/g, '-')"
                                        @click="addIdentifier(target)"
                                        >{{ mappingTargets()[target].label }}</a
                                    >
                                </div>
                                <b-button
                                    v-b-tooltip.hover.bottom
                                    :title="titleApplyColumnDefinitions"
                                    class="rule-mapping-ok"
                                    v-if="!hasActiveMappingEdit"
                                    @click="displayRuleType = null"
                                    >{{ l("Apply") }}</b-button
                                >
                            </div>
                        </div>
                        <div class="rule-summary" v-if="displayRuleType == null">
                            <span class="title">
                                {{ l("Rules") }}
                                <span
                                    v-b-tooltip.hover
                                    class="fa fa-wrench rule-builder-view-source"
                                    :title="titleViewSource"
                                    @click="viewSource"
                                ></span>
                                <saved-rules-selector
                                    ref="savedRulesSelector"
                                    @update-rules="restoreRules"
                                    :savedRules="this.savedRules"
                                />
                            </span>
                            <div v-if="jaggedData" class="rule-warning">
                                Rows contain differing numbers of columns, there was likely a problem parsing your data.
                            </div>
                            <ol class="rules">
                                <!-- Example at the end of https://vuejs.org/v2/guide/list.html -->
                                <rule-display
                                    v-for="(rule, index) in rules"
                                    :rule="rule"
                                    :index="index"
                                    :key="index"
                                    @edit="editRule(rule, index)"
                                    @remove="removeRule(index)"
                                    :col-headers="colHeadersPerRule[index]"
                                />
                                <identifier-display
                                    v-for="(map, index) in mapping"
                                    v-bind="map"
                                    :index="index"
                                    :key="map.type"
                                    @remove="removeMapping(index)"
                                    @edit="displayRuleType = 'mapping'"
                                    @mouseover.native="map.columns.forEach((col) => highlightColumn(col))"
                                    @mouseout.native="map.columns.forEach((col) => unhighlightColumn(col))"
                                    :col-headers="colHeaders"
                                />
                                <div v-if="mapping.length == 0">
                                    One or more column definitions must be specified. These are required to specify how
                                    to build collections and datasets from rows and columns of the table.
                                    <a href="javascript:void(0)" @click="displayRuleType = 'mapping'">Click here</a> to
                                    manage column definitions.
                                </div>
                            </ol>
                            <div class="rules-buttons btn-group">
                                <div class="dropup">
                                    <button
                                        type="button"
                                        v-b-tooltip.hover.bottom
                                        :title="titleRulesMenu"
                                        class="rule-menu-rules-button primary-button dropdown-toggle"
                                        data-toggle="dropdown"
                                    >
                                        <span class="fa fa-plus"></span>
                                        {{ l("Rules") }}
                                        <span class="caret"></span>
                                    </button>
                                    <div class="dropdown-menu" role="menu">
                                        <rule-target-component :builder="this" rule-type="sort" />
                                        <rule-target-component :builder="this" rule-type="remove_columns" />
                                        <rule-target-component :builder="this" rule-type="split_columns" />
                                        <rule-target-component :builder="this" rule-type="swap_columns" />
                                        <a
                                            href="javascript:void(0)"
                                            class="dropdown-item rule-link rule-link-mapping"
                                            @click="displayRuleType = 'mapping'"
                                            >Add / Modify Column Definitions</a
                                        >
                                    </div>
                                </div>
                                <div class="dropup">
                                    <button
                                        type="button"
                                        v-b-tooltip.hover.bottom
                                        :title="titleFilterMenu"
                                        class="rule-menu-filter-button primary-button dropdown-toggle"
                                        data-toggle="dropdown"
                                    >
                                        <span class="fa fa-plus"></span>
                                        {{ l("Filter") }}
                                        <span class="caret"></span>
                                    </button>
                                    <div class="dropdown-menu" role="menu">
                                        <rule-target-component :builder="this" rule-type="add_filter_regex" />
                                        <rule-target-component :builder="this" rule-type="add_filter_matches" />
                                        <rule-target-component :builder="this" rule-type="add_filter_compare" />
                                        <rule-target-component :builder="this" rule-type="add_filter_empty" />
                                        <rule-target-component :builder="this" rule-type="add_filter_count" />
                                    </div>
                                </div>
                                <div class="dropup">
                                    <button
                                        type="button"
                                        v-b-tooltip.hover.bottom
                                        :title="titleColumMenu"
                                        class="rule-menu-column-button primary-button dropdown-toggle"
                                        data-toggle="dropdown"
                                    >
                                        <span class="fa fa-plus"></span>
                                        {{ l("Column") }}
                                        <span class="caret"></span>
                                    </button>
                                    <div class="dropdown-menu" role="menu">
                                        <rule-target-component :builder="this" rule-type="add_column_basename" />
                                        <rule-target-component
                                            :builder="this"
                                            rule-type="add_column_metadata"
                                            v-if="metadataOptions"
                                        />
                                        <rule-target-component
                                            :builder="this"
                                            rule-type="add_column_group_tag_value"
                                            v-if="hasTagsMetadata"
                                        />
                                        <rule-target-component :builder="this" rule-type="add_column_regex" />
                                        <rule-target-component :builder="this" rule-type="add_column_concatenate" />
                                        <rule-target-component :builder="this" rule-type="add_column_rownum" />
                                        <rule-target-component :builder="this" rule-type="add_column_value" />
                                        <rule-target-component :builder="this" rule-type="add_column_substr" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <!--  flex-column column -->
                <!--  style="width: 70%;" -->
                <div class="table-column" :class="orientation" style="width: 100%;" v-if="initialElements !== null">
                    <hot-table
                        id="hot-table"
                        ref="hotTable"
                        :data="hotData.data"
                        :col-headers="colHeadersDisplay"
                        :read-only="true"
                        stretch-h="all"
                    ></hot-table>
                </div>
            </div>
        </rule-modal-middle>
        <rule-modal-footer v-if="ruleView == 'source'">
            <b-button v-b-tooltip.hover :title="titleSourceCancel" @click="cancelSourceEdit" class="rule-btn-cancel">{{
                l("Cancel")
            }}</b-button>
            <b-button v-b-tooltip.hover :title="titleSourceReset" class="creator-reset-btn rule-btn-reset">{{
                l("Reset")
            }}</b-button>
            <b-button v-b-tooltip.hover :title="titleSourceApply" @click="attemptRulePreview" class="rule-btn-okay">{{
                l("Apply")
            }}</b-button>
        </rule-modal-footer>
        <rule-modal-footer v-else-if="ruleView == 'normal'">
            <template v-slot:inputs>
                <div class="rule-footer-inputs">
                    <label v-if="elementsType == 'datasets'">{{ l("Hide original elements") }}:</label>
                    <input type="checkbox" v-model="hideSourceItems" v-if="elementsType == 'datasets'" />
                    <div class="rule-footer-extension-group" v-if="extension && showFileTypeSelector">
                        <label>{{ l("Type") }}:</label>
                        <select2 name="extension" class="extension-select" v-model="extension">
                            <option v-for="col in extensions" :value="col['id']" :key="col.id">
                                {{ col["text"] }}
                            </option>
                        </select2>
                    </div>
                    <div class="rule-footer-genome-group" v-if="genome && showGenomeSelector">
                        <label>{{ l("Genome") }}:</label>
                        <select2 class="genome-select" v-model="genome">
                            <option v-for="col in genomes" :value="col['id']" :key="col.id">{{ col["text"] }}</option>
                        </select2>
                    </div>
                    <label v-if="showAddNameTag">{{ l("Add nametag for name") }}:</label>
                    <input type="checkbox" v-model="addNameTag" v-if="showAddNameTag" />
                    <div class="rule-footer-name-group" v-if="showCollectionNameInput">
                        <b-input
                            class="collection-name"
                            :placeholder="namePlaceholder"
                            :title="namePlaceholder"
                            v-b-tooltip.hover
                            v-model="collectionName"
                        />
                        <label>{{ l("Name") }}:</label>
                    </div>
                </div>
            </template>

            <b-button
                v-b-tooltip.hover
                :help="titleCancel"
                @click="cancel"
                class="creator-cancel-btn rule-btn-cancel"
                tabindex="-1"
                >{{ l("Cancel") }}</b-button
            >
            <b-button
                v-b-tooltip.hover
                @click="resetRulesAndState"
                :title="titleReset"
                class="creator-reset-btn rule-btn-reset"
                >{{ l("Reset") }}</b-button
            >
            <!--https://github.com/bootstrap-vue/bootstrap-vue/issues/2937#issuecomment-478577527-->
            <b-button
                v-b-tooltip.hover.d50
                @click="createCollection"
                :title="titleFinish"
                class="create-collection rule-btn-okay"
                variant="primary"
                :disabled="!validInput"
                >{{ finishButtonTitle }}</b-button
            >
        </rule-modal-footer>
    </state-div>
    <state-div v-else-if="state == 'wait'">
        <rule-modal-header v-if="importType == 'datasets'">
            {{
                l(
                    "Datasets submitted to Galaxy for creation, this dialog will close when dataset creation is complete. You may close this dialog at any time, but you will not be informed of errors with dataset creation and you may have to refresh your history manually to view new datasets once complete."
                )
            }}
        </rule-modal-header>
        <rule-modal-header v-else-if="importType == 'collections'">
            {{
                l(
                    "Galaxy is waiting for collection creation, this dialog will close when this is complete. You may close this dialog at any time, but you will not be informed of errors with collection creation and you may have to refresh your history manually to view new collections once complete."
                )
            }}
        </rule-modal-header>
        <rule-modal-footer>
            <b-button @click="cancel" class="creator-cancel-btn" tabindex="-1">{{ l("Close") }}</b-button>
        </rule-modal-footer>
    </state-div>
    <state-div v-else-if="state == 'error'">
        <!-- TODO: steal styling from paired collection builder warning... -->
        <rule-modal-header>A problem was encountered.</rule-modal-header>
        <rule-modal-middle>
            <p class="errormessagelarge">{{ errorMessage }}</p>
        </rule-modal-middle>
        <rule-modal-footer>
            <b-button v-b-tooltip.hover :title="titleCancel" @click="cancel" class="creator-cancel-btn" tabindex="-1">{{
                l("Close")
            }}</b-button>
            <b-button v-b-tooltip.hover :title="titleErrorOkay" @click="state = 'build'" tabindex="-1">{{
                l("Okay")
            }}</b-button>
        </rule-modal-footer>
    </state-div>
</template>
<script>
import $ from "jquery";
import _ from "underscore";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import AjaxQueue from "utils/ajax-queue";
import axios from "axios";
import _l from "utils/localization";
import HotTable from "@handsontable/vue";
import UploadUtils from "mvc/upload/upload-utils";
import JobStatesModel from "mvc/history/job-states-model";
import RuleDefs from "mvc/rules/rule-definitions";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import Select2 from "components/Select2";
import ColumnSelector from "components/RuleBuilder/ColumnSelector";
import RegularExpressionInput from "components/RuleBuilder/RegularExpressionInput";
import RuleDisplay from "components/RuleBuilder/RuleDisplay";
import IdentifierDisplay from "components/RuleBuilder/IdentifierDisplay";
import RuleTargetComponent from "components/RuleBuilder/RuleTargetComponent";
import RuleComponent from "components/RuleBuilder/RuleComponent";
import RuleModalHeader from "components/RuleBuilder/RuleModalHeader";
import RuleModalMiddle from "components/RuleBuilder/RuleModalMiddle";
import RuleModalFooter from "components/RuleBuilder/RuleModalFooter";
import StateDiv from "components/RuleBuilder/StateDiv";
import SavedRulesSelector from "components/RuleBuilder/SavedRulesSelector";
import SaveRules from "components/RuleBuilder/SaveRules";

Vue.use(BootstrapVue);

const RULES = RuleDefs.RULES;
const MAPPING_TARGETS = RuleDefs.MAPPING_TARGETS;

export default {
    data: function () {
        let orientation = "vertical";
        let mapping;
        let rules;
        if (this.initialRules) {
            mapping = this.initialRules.mapping.slice();
            rules = this.initialRules.rules.slice();
        } else {
            if (this.elementsType == "ftp") {
                mapping = [{ type: "ftp_path", columns: [0] }];
            } else if (this.elementsType == "remote_files") {
                mapping = [{ type: "url", columns: [0] }];
            } else if (this.elementsType == "datasets") {
                mapping = [{ type: "list_identifiers", columns: [1] }];
            } else {
                mapping = [];
            }
            rules = [];
            if (this.elementsType == "collection_contents") {
                if (this.initialElements !== null) {
                    const collectionType = this.initialElements.collection_type;
                    const collectionTypeRanks = collectionType.split(":");
                    for (const index in collectionTypeRanks) {
                        rules.push({
                            type: "add_column_metadata",
                            value: "identifier" + index,
                        });
                    }
                } else {
                    orientation = "horizontal";
                    // just assume a list is given by default.
                    rules.push({
                        type: "add_column_metadata",
                        value: "identifier0",
                    });
                }
            } else if (this.elementsType == "datasets") {
                rules.push(
                    {
                        type: "add_column_metadata",
                        value: "hid",
                    },
                    {
                        type: "add_column_metadata",
                        value: "name",
                    }
                );
            } else if (this.elementsType == "library_datasets") {
                rules.push({
                    type: "add_column_metadata",
                    value: "name",
                });
            } else if (this.elementsType == "ftp") {
                rules.push({
                    type: "add_column_metadata",
                    value: "path",
                });
            } else if (this.elementsType == "remote_files") {
                rules.push({
                    type: "add_column_metadata",
                    value: "uri",
                });
            }
        }
        return {
            rules: rules,
            mapping: mapping,
            state: "build", // 'build', 'error', 'wait',
            ruleView: "normal", // 'normal' or 'source'
            ruleSource: "",
            ruleSourceJson: null,
            ruleSourceError: null,
            errorMessage: "",
            jaggedData: false,
            waitingJobState: "new",
            titleReset: _l("Undo all reordering and discards"),
            titleNumericSort: _l(
                "By default columns will be sorted lexicographically, check this option if the columns are numeric values and should be sorted as numbers"
            ),
            titleInvertFilterRegex: _l("Remove rows not matching the specified regular expression at specified column"),
            titleInvertFilterEmpty: _l("Remove rows that have non-empty values at specified column"),
            titleInvertFilterMatches: _l("Remove rows not matching supplied value"),
            titleViewSource: _l(
                "Advanced Option: View and or edit the JSON representation of the rules to apply to this tabular data"
            ),
            titleSourceCancel: _l("Stop editing rules and dismiss changes"),
            titleSourceReset: _l("Reset text area to current set of rules"),
            titleSourceApply: _l("Apply changes to rule source and return to rule preview"),
            titleRulesMenu: _l("General rules to apply"),
            titleFilterMenu: _l("Rules that filter rows from the data"),
            titleColumMenu: _l("Rules that generate new columns"),
            titleRemoveMapping: _l("Remove column definition assignment"),
            titleApplyColumnDefinitions: _l("Apply these column definitions and return to rules preview"),
            titleErrorOkay: _l("Dismiss this error and return to the rule builder to try again with new rules"),
            namePlaceholder: _l("Enter a name for your new collection"),
            activeRuleIndex: null,
            addColumnRegexTarget: 0,
            addColumnBasenameTarget: 0,
            addColumnRegexExpression: "",
            addColumnRegexReplacement: null,
            addColumnRegexGroupCount: null,
            addColumnRegexType: "global",
            addColumnMetadataValue: 0,
            addColumnGroupTagValueValue: "",
            addColumnGroupTagValueDefault: "",
            addColumnConcatenateTarget0: 0,
            addColumnConcatenateTarget1: 0,
            addColumnRownumStart: 1,
            addColumnSubstrTarget: 0,
            addColumnSubstrType: "keep_prefix",
            addColumnSubstrLength: 1,
            addColumnValue: "",
            removeColumnTargets: [],
            addFilterRegexTarget: 0,
            addFilterRegexExpression: "",
            addFilterRegexInvert: false,
            addFilterMatchesTarget: 0,
            addFilterMatchesValue: "",
            addFilterMatchesInvert: false,
            addFilterEmptyTarget: 0,
            addFilterEmptyInvert: false,
            addFilterCompareTarget: 0,
            addFilterCompareValue: 0,
            addFilterCompareType: "less_than",
            addFilterCountN: 1,
            addFilterCountInvert: false,
            addFilterCountWhich: "first",
            addSortingTarget: 0,
            addSortingNumeric: false,
            splitColumnsTargets0: [],
            splitColumnsTargets1: [],
            swapColumnsTarget0: 0,
            swapColumnsTarget1: 0,
            collectionName: "",
            displayRuleType: null,
            extensions: [],
            extension: null,
            genomes: [],
            genome: null,
            hideSourceItems: this.defaultHideSourceItems,
            addNameTag: false,
            orientation: orientation,
        };
    },
    props: {
        initialElements: {
            required: true,
        },
        importType: {
            type: String,
            required: false,
            default: "collections",
        },
        elementsType: {
            type: String,
            required: false,
            default: "datasets",
        },
        // required if elementsType is "datasets" - hook into Backbone code for creating
        // collections from HDAs, etc...
        creationFn: {
            required: false,
            type: Function,
        },
        // required if elementsType is "collection_contents" - hook into tool form to update
        // rule parameter
        saveRulesFn: {
            required: false,
            type: Function,
        },
        initialRules: {
            required: false,
            type: Object,
        },
        defaultHideSourceItems: {
            type: Boolean,
            required: false,
            default: true,
        },
        // Callbacks sent in by modal code.
        oncancel: {
            required: true,
            type: Function,
        },
        oncreate: {
            required: true,
            type: Function,
        },
        ftpUploadSite: {
            type: String,
            required: false,
            default: null,
        },
    },
    computed: {
        exisistingDatasets() {
            const elementsType = this.elementsType;
            return (
                elementsType === "datasets" ||
                elementsType === "collection_contents" ||
                elementsType === "library_datasets"
            );
        },
        showFileTypeSelector() {
            return !this.exisistingDatasets && !this.mappingAsDict.file_type;
        },
        showGenomeSelector() {
            return !this.exisistingDatasets && !this.mappingAsDict.dbkey;
        },
        showCollectionNameInput() {
            return (
                this.importType == "collections" &&
                this.elementsType != "collection_contents" &&
                !this.mappingAsDict.collection_name
            );
        },
        showAddNameTag() {
            return this.importType == "collections" && this.elementsType != "collection_contents";
        },
        titleFinish() {
            if (this.elementsType == "datasets" || this.elementsType == "library_datasets") {
                return _l("Create new collection from specified rules and datasets");
            } else if (this.elementsType == "collection_contents") {
                return _l("Save rules and return to tool form");
            } else {
                return _l("Upload collection using specified rules");
            }
        },
        titleCancel() {
            if (this.importType == "datasets") {
                return _l("Close this modal and do not upload any datasets");
            } else {
                return _l("Close this modal and do not create any collections");
            }
        },
        finishButtonTitle() {
            if (this.elementsType == "datasets" || this.elementsType == "library_datasets") {
                return _l("Create");
            } else if (this.elementsType == "collection_contents") {
                return _l("Save");
            } else {
                return _l("Upload");
            }
        },
        hasActiveMappingEdit() {
            const has = _.any(_.values(this.mapping), (mapping) => mapping.editing);
            return has;
        },
        activeRule() {
            return this.activeRuleIndex !== null && this.rules[this.activeRuleIndex];
        },
        activeRuleColHeaders() {
            const rulesHeaders = this.activeRuleIndex !== null && this.colHeadersPerRule[this.activeRuleIndex];
            return rulesHeaders || this.colHeaders;
        },
        horizontal() {
            return this.orientation == "horizontal";
        },
        vertical() {
            return this.orientation == "vertical";
        },
        mappedTargets() {
            const targets = [];
            for (const mapping of this.mapping) {
                targets.push(mapping.type);
            }
            return targets;
        },
        unmappedTargets() {
            const targets = [];
            const mappedTargets = this.mappedTargets;
            for (const target in MAPPING_TARGETS) {
                const targetModes = MAPPING_TARGETS[target].modes;

                if (targetModes && targetModes.indexOf(this.elementsType) < 0) {
                    continue;
                }

                const targetDefinition = MAPPING_TARGETS[target];
                const targetImportType = targetDefinition.importType;
                if (targetImportType && this.importType != targetImportType) {
                    continue;
                }
                if (!this.ftpUploadSite && targetDefinition.requiresFtp) {
                    continue;
                }
                if (mappedTargets.indexOf(target) < 0) {
                    targets.push(target);
                }
            }
            return targets;
        },
        colHeaders() {
            const { data, columns } = this.hotData;
            return RuleDefs.colHeadersFor(data, columns);
        },
        colHeadersDisplay() {
            const formattedHeaders = [];
            for (const colIndex in this.colHeaders) {
                const colHeader = this.colHeaders[colIndex];
                formattedHeaders[colIndex] = `<b>${_.escape(colHeader)}</b>`;
                const mappingDisplay = [];
                for (const mapping of this.mapping) {
                    if (mapping.columns.indexOf(parseInt(colIndex)) !== -1) {
                        const mappingDef = MAPPING_TARGETS[mapping.type];
                        mappingDisplay.push(`<i>${_.escape(mappingDef.columnHeader || mappingDef.label)}</i>`);
                    }
                }
                if (mappingDisplay.length == 1) {
                    formattedHeaders[colIndex] += ` (${mappingDisplay[0]})`;
                } else if (mappingDisplay.length > 1) {
                    formattedHeaders[colIndex] += ` (${[
                        mappingDisplay.slice(0, -1).join(", "),
                        mappingDisplay.slice(-1)[0],
                    ].join(" & ")})`;
                }
            }
            return formattedHeaders;
        },
        mappingAsDict() {
            const asDict = {};
            for (const mapping of this.mapping) {
                asDict[mapping.type] = mapping;
            }
            return asDict;
        },
        metadataOptions() {
            let metadataOptions = {};
            if (this.elementsType == "collection_contents") {
                let collectionType;
                if (this.initialElements) {
                    collectionType = this.initialElements.collection_type;
                } else {
                    // give a bunch of different options if not constrained with given input
                    collectionType = "list:list:list:paired";
                }
                const collectionTypeRanks = collectionType.split(":");
                for (const index in collectionTypeRanks) {
                    const collectionTypeRank = collectionTypeRanks[index];
                    if (collectionTypeRank == "list") {
                        // TODO: drop the numeral at the end if only flat list
                        metadataOptions["identifier" + index] = _l("List Identifier ") + (parseInt(index) + 1);
                    } else {
                        metadataOptions["identifier" + index] = _l("Paired Identifier");
                    }
                }
                metadataOptions["tags"] = _l("Tags");
            } else if (this.elementsType == "ftp") {
                metadataOptions["path"] = _l("Path");
            } else if (this.elementsType == "remote_files") {
                // IS THIS NEEDED?
                metadataOptions["url"] = _l("URL");
            } else if (this.elementsType == "library_datasets") {
                metadataOptions["name"] = _l("Name");
            } else if (this.elementsType == "datasets") {
                metadataOptions["hid"] = _l("History ID (hid)");
                metadataOptions["name"] = _l("Name");
            } else {
                metadataOptions = null;
            }
            return metadataOptions;
        },
        hasTagsMetadata() {
            // TODO: allow for dataset, library_datasets also - here and just above in metadataOptions.
            return this.elementsType == "collection_contents";
        },
        collectionType() {
            let identifierColumns = [];
            if (this.mappingAsDict.list_identifiers) {
                identifierColumns = this.mappingAsDict.list_identifiers.columns;
            }
            let collectionType = identifierColumns.map((col) => "list").join(":");
            if (this.mappingAsDict.paired_identifier) {
                if (collectionType) {
                    collectionType += ":paired";
                } else {
                    collectionType = "paired";
                }
            }
            return collectionType;
        },
        validInput() {
            const identifierColumns = this.identifierColumns();
            const mappingAsDict = this.mappingAsDict;
            const buildingCollection = this.importType == "collections";
            const requiresName =
                buildingCollection && this.elementsType != "collection_contents" && !mappingAsDict.collection_name;

            let valid = true;
            if (requiresName) {
                valid = this.collectionName.length > 0;
            }

            if (mappingAsDict.ftp_path && mappingAsDict.url) {
                // Can only specify one of these.
                valid = false;
            }

            const requiresSourceColumn =
                this.elementsType == "ftp" || this.elementsType == "raw" || this.elementsType == "remote_files";
            if (requiresSourceColumn && !mappingAsDict.ftp_path && !mappingAsDict.url) {
                valid = false;
            }
            for (const rule of this.rules) {
                if (rule.error) {
                    valid = false;
                }
            }

            if (buildingCollection && identifierColumns.length == 0) {
                valid = false;
            }
            return valid;
        },
        hotData() {
            let data;
            let sources;
            let columns;
            if (
                this.elementsType == "datasets" ||
                this.elementsType == "library_datasets" ||
                this.elementsType == "ftp" ||
                this.elementsType == "remote_files"
            ) {
                sources = this.initialElements.slice();
                data = sources.map((el) => []);
                columns = [];
            } else if (this.elementsType == "collection_contents") {
                const collection = this.initialElements;
                if (collection) {
                    const obj = this.populateElementsFromCollectionDescription(
                        collection.elements,
                        collection.collection_type
                    );
                    data = obj.data;
                    sources = obj.sources;
                    columns = [];
                } else {
                    data = [];
                    sources = [];
                    columns = [];
                }
            } else {
                data = this.initialElements.slice();
                sources = data.map((el) => null);
                columns = [];
                if (this.initialElements) {
                    this.initialElements[0].forEach(() => columns.push("new"));
                }
            }
            return RuleDefs.applyRules(data, sources, columns, this.rules);
        },
        colHeadersPerRule() {
            return this.hotData.colHeadersPerRule;
        },
    },
    mixins: [SaveRules],
    methods: {
        restoreRules(event) {
            const json = JSON.parse(event);
            this.rules = json.rules;
            this.mapping = json.mapping;
        },
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        cancel() {
            this.oncancel();
        },
        mappingTargets() {
            return MAPPING_TARGETS;
        },
        resetRules() {
            this.rules.splice(0, this.rules.length);
            this.mapping.splice(0, this.mapping.length);
        },
        resetRulesAndState() {
            this.resetRules();
            this.state = "build";
            this.errorMessage = "";
            this.collectionName = "";
        },
        addNewRule(ruleType) {
            RULES[ruleType].init(this);
            this.displayRuleType = ruleType;
            this.activeRuleIndex = null;
        },
        handleRuleSave(ruleType) {
            const rule = this.activeRule;
            if (rule) {
                RULES[ruleType].save(this, rule);
            } else {
                const rule = { type: ruleType };
                RULES[ruleType].save(this, rule);
                this.rules.push(rule);
            }
        },
        viewSource() {
            this.resetSource();
            this.ruleView = "source";
        },
        resetSource() {
            const replacer = function (key, value) {
                if (key == "error" || key == "warn") {
                    return undefined;
                }
                return value;
            };
            const asJson = {
                rules: this.rules,
                mapping: this.mapping,
            };
            if (!this.exisistingDatasets) {
                if (this.extension !== UploadUtils.DEFAULT_EXTENSION) {
                    asJson.extension = this.extension;
                }
                if (this.genome !== UploadUtils.DEFAULT_GENOME) {
                    asJson.genome = this.genome;
                }
            }
            this.ruleSourceJson = asJson;
            this.ruleSource = JSON.stringify(asJson, replacer, "  ");
            this.ruleSourceError = null;
        },
        attemptRulePreview() {
            // Leave source mode if rules are valid and view.
            this.ruleSourceError = null;
            let asJson;
            try {
                asJson = JSON.parse(this.ruleSource);
            } catch (error) {
                this.ruleSourceError = "Problem parsing your rules.";
                return;
            }
            this.updateFromSource(asJson);
            this.ruleView = "normal";
        },
        cancelSourceEdit() {
            this.ruleSourceError = null;
            this.ruleView = "normal";
        },
        updateFromSource(asJson) {
            this.resetRules();
            if (asJson.extension) {
                this.extension = asJson.extension;
            }
            if (asJson.genome) {
                this.genome = asJson.genome;
            }
            if (asJson.rules) {
                this.rules = asJson.rules;
            }
            if (asJson.mapping) {
                this.mapping = asJson.mapping;
            }
        },
        addIdentifier(identifier) {
            const multiple = this.mappingTargets()[identifier].multiple;
            // If multiple selection, pop open a new column selector in edit mode.
            const initialColumns = multiple ? [] : [0];
            this.mapping.push({ type: identifier, columns: initialColumns, editing: multiple });
        },
        editRule(rule, index) {
            const ruleType = rule.type;
            this.activeRuleIndex = index;
            RULES[ruleType].init(this, rule);
            this.displayRuleType = ruleType;
        },
        removeRule(index) {
            this.rules.splice(index, 1);
        },
        removeMapping(index) {
            this.mapping.splice(index, 1);
        },
        refreshAndWait(response) {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.currHistoryPanel) {
                Galaxy.currHistoryPanel.refreshContents();
            }
            this.waitOnJob(response);
        },
        waitOnJob(response) {
            const jobId = response.data.jobs[0].id;
            const handleJobShow = (jobResponse) => {
                const state = jobResponse.data.state;
                this.waitingJobState = state;
                if (JobStatesModel.NON_TERMINAL_STATES.indexOf(state) !== -1) {
                    setTimeout(doJobCheck, 1000);
                } else if (JobStatesModel.ERROR_STATES.indexOf(state) !== -1) {
                    this.state = "error";
                    this.errorMessage =
                        "Unknown error encountered while running your upload job, this could be a server issue or a problem with the upload definition.";
                    this.doFullJobCheck(jobId);
                } else {
                    const Galaxy = getGalaxyInstance();
                    const history = Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model;
                    history.refresh();
                    this.oncreate();
                }
            };
            const doJobCheck = () => {
                axios.get(`${getAppRoot()}api/jobs/${jobId}`).then(handleJobShow).catch(this.renderFetchError);
            };
            setTimeout(doJobCheck, 1000);
        },
        doFullJobCheck(jobId) {
            const handleJobShow = (jobResponse) => {
                const stderr = jobResponse.data.stderr;
                if (stderr) {
                    let errorMessage = "An error was encountered while running your upload job. ";
                    if (stderr.indexOf("binary file contains inappropriate content") > -1) {
                        errorMessage +=
                            "The problem may be that the batch uploader will not automatically decompress your files the way the normal uploader does, please specify a correct extension or upload decompressed data.";
                    }
                    errorMessage += "Upload job completed with standard error: " + stderr;
                    this.errorMessage = errorMessage;
                }
            };
            axios.get(`${getAppRoot()}api/jobs/${jobId}?full=True`).then(handleJobShow).catch(this.renderFetchError);
        },
        renderFetchError(error) {
            this.state = "error";
            if (error.response) {
                console.log(error.response);
                this.errorMessage = error.response.data.err_msg;
            } else {
                console.log(error);
                this.errorMessage = "Unknown error encountered: " + error;
            }
        },
        swapOrientation() {
            this.orientation = this.orientation == "horizontal" ? "vertical" : "horizontal";
            const hotTable = this.$refs.hotTable.table;
            if (this.orientation == "horizontal") {
                this.$nextTick(function () {
                    const fullWidth = $(".rule-builder-body").width();
                    hotTable.updateSettings({
                        width: fullWidth,
                    });
                });
            } else {
                this.$nextTick(function () {
                    const fullWidth = $(".rule-builder-body").width();
                    hotTable.updateSettings({
                        width: fullWidth - 270,
                    });
                });
            }
        },
        createCollection() {
            const asJson = {
                rules: this.rules,
                mapping: this.mapping,
            };
            var arrayOfColumns = this.mapping.flatMap((m) => m.columns);
            if (arrayOfColumns.some((m) => m >= this.colHeaders.length)) {
                this.errorMessage = "You have undefined columns in your rules.";
                this.state = "error";
                return;
            }
            this.saveSession(JSON.stringify(asJson));
            this.state = "wait";
            const name = this.collectionName;
            const collectionType = this.collectionType;
            if (this.elementsType == "datasets" || this.elementsType == "library_datasets") {
                const elements = this.creationElementsFromDatasets();
                if (this.state !== "error") {
                    new AjaxQueue.AjaxQueue(
                        _.map(elements, (elements, name) => {
                            return () => {
                                const response = this.creationFn(elements, collectionType, name, this.hideSourceItems);
                                return response;
                            };
                        })
                    )
                        .done(this.oncreate)
                        .fail(this.renderFetchError);
                }
            } else if (this.elementsType == "collection_contents") {
                this.resetSource();
                if (this.state !== "error") {
                    this.saveRulesFn(this.ruleSourceJson);
                    this.oncreate();
                }
            } else {
                const Galaxy = getGalaxyInstance();
                const historyId = Galaxy.currHistoryPanel.model.id;
                let elements;
                let targets;
                if (collectionType) {
                    targets = [];
                    const elementsByCollectionName = this.creationElementsForFetch();
                    for (const collectionName in elementsByCollectionName) {
                        const target = {
                            destination: { type: "hdca" },
                            elements: elementsByCollectionName[collectionName],
                            collection_type: collectionType,
                            name: collectionName,
                        };
                        if (this.addNameTag) {
                            target["tags"] = ["name:" + collectionName];
                        }
                        targets.push(target);
                    }
                } else {
                    elements = this.creationDatasetsForFetch();
                    targets = [
                        {
                            destination: { type: "hdas" },
                            elements: elements,
                            name: name,
                        },
                    ];
                }

                if (this.state !== "error") {
                    axios
                        .post(`${getAppRoot()}api/tools/fetch`, {
                            history_id: historyId,
                            targets: targets,
                            auto_decompress: true,
                        })
                        .then(this.refreshAndWait)
                        .catch(this.renderFetchError);
                }
            }
        },
        identifierColumns() {
            const mappingAsDict = this.mappingAsDict;
            let identifierColumns = [];
            if (mappingAsDict.list_identifiers) {
                identifierColumns = mappingAsDict.list_identifiers.columns.slice();
            }
            if (this.mappingAsDict.paired_identifier) {
                identifierColumns.push(this.mappingAsDict.paired_identifier.columns[0]);
            }
            return identifierColumns;
        },
        buildRequestElements(createDatasetDescription, createSubcollectionDescription, subElementProp) {
            const data = this.hotData.data;
            const identifierColumns = this.identifierColumns();
            if (identifierColumns.length < 1) {
                console.log("Error but this shouldn't have happened, create button should have been disabled.");
                return;
            }

            const numIdentifierColumns = identifierColumns.length;
            const collectionType = this.collectionType;
            const elementsByName = {};

            const dataByCollection = {};
            const collectionNameMap = this.mappingAsDict.collection_name;
            if (collectionNameMap) {
                const collectionNameTarget = collectionNameMap.columns[0];
                for (const dataIndex in data) {
                    const row = data[dataIndex];
                    const name = row[collectionNameTarget];
                    if (!dataByCollection[name]) {
                        dataByCollection[name] = {};
                    }
                    dataByCollection[name][dataIndex] = row;
                }
            } else {
                // use global collection name from the form.
                dataByCollection[this.collectionName] = data;
            }

            for (const collectionName in dataByCollection) {
                const elements = [];
                const identifiers = [];

                for (const dataIndex in dataByCollection[collectionName]) {
                    const rowData = data[dataIndex];

                    // For each row, find place in depth for this element.
                    let collectionTypeAtDepth = collectionType;
                    let elementsAtDepth = elements;
                    let identifiersAtDepth = identifiers;

                    for (
                        let identifierColumnIndex = 0;
                        identifierColumnIndex < numIdentifierColumns;
                        identifierColumnIndex++
                    ) {
                        // typeof indicates identifier is a string, but the raw string value coming from this data
                        // structure sometimes does not work as expected with indexOf below, I don't understand why
                        // but as a result this cast here seems needed.
                        let identifier = String(rowData[identifierColumns[identifierColumnIndex]]);
                        if (identifierColumnIndex + 1 == numIdentifierColumns) {
                            // At correct final position in nested structure for this dataset.
                            if (collectionTypeAtDepth === "paired") {
                                if (["f", "1", "r1", "forward"].indexOf(identifier.toLowerCase()) > -1) {
                                    identifier = "forward";
                                } else if (["r", "2", "r2", "reverse"].indexOf(identifier.toLowerCase()) > -1) {
                                    identifier = "reverse";
                                } else {
                                    this.state = "error";
                                    this.errorMessage =
                                        "Unknown indicator of paired status encountered - only values of F, R, 1, 2, R1, R2, forward, or reverse are allowed.";
                                    return;
                                }
                            }
                            const element = createDatasetDescription(dataIndex, identifier);
                            elementsAtDepth.push(element);
                            if (identifiersAtDepth.indexOf(identifier) >= 0) {
                                this.state = "error";
                                this.errorMessage =
                                    "Duplicate identifiers detected, collection identifiers must be unique.";
                                return;
                            }
                            identifiersAtDepth.push(identifier);
                        } else {
                            // Create nesting for this element.
                            collectionTypeAtDepth = collectionTypeAtDepth.split(":").slice(1).join(":");
                            let found = false;
                            for (const element of elementsAtDepth) {
                                if (element["name"] == identifier) {
                                    elementsAtDepth = element[subElementProp];
                                    identifiersAtDepth = identifiersAtDepth[identifier];
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                const subcollection = createSubcollectionDescription(identifier);
                                elementsAtDepth.push(subcollection);
                                identifiersAtDepth[identifier] = [];
                                const childCollectionElements = [];
                                subcollection[subElementProp] = childCollectionElements;
                                subcollection.collection_type = collectionTypeAtDepth;
                                elementsAtDepth = childCollectionElements;
                                identifiersAtDepth = identifiersAtDepth[identifier];
                            }
                        }
                    }
                }

                elementsByName[collectionName] = elements;
            }

            return elementsByName;
        },
        creationElementsFromDatasets() {
            const { sources, data } = this.hotData;
            const mappingAsDict = this.mappingAsDict;

            const elementsByCollectionName = this.buildRequestElements(
                (dataIndex, identifier) => {
                    const source = sources[dataIndex];
                    const res = this._datasetFor(dataIndex, data, mappingAsDict);
                    const src = this.elementsType == "datasets" ? "hda" : "ldda";
                    return { id: source["id"], name: identifier, src: src, tags: res.tags };
                },
                (identifier) => {
                    return { name: identifier, src: "new_collection" };
                },
                "element_identifiers"
            );
            return elementsByCollectionName;
        },
        creationElementsForFetch() {
            // fetch elements for HDCA
            const data = this.hotData.data;
            const mappingAsDict = this.mappingAsDict;

            const elementsByCollectionName = this.buildRequestElements(
                (dataIndex, identifier) => {
                    const res = this._datasetFor(dataIndex, data, mappingAsDict);
                    res["name"] = identifier;
                    return res;
                },
                (identifier) => {
                    return { name: identifier };
                },
                "elements"
            );

            return elementsByCollectionName;
        },
        creationDatasetsForFetch() {
            // fetch elements for HDAs if not collection information specified.
            const data = this.hotData.data;
            const mappingAsDict = this.mappingAsDict;

            const datasets = [];

            for (const dataIndex in data) {
                const res = this._datasetFor(dataIndex, data, mappingAsDict);
                datasets.push(res);
            }

            return datasets;
        },
        populateElementsFromCollectionDescription(elements, collectionType, parentIdentifiers_) {
            const parentIdentifiers = parentIdentifiers_ ? parentIdentifiers_ : [];
            let data = [];
            let sources = [];
            for (const element of elements) {
                const elementObject = element.object;
                const identifiers = parentIdentifiers.concat([element.element_identifier]);
                const collectionTypeLevelSepIndex = collectionType.indexOf(":");
                if (collectionTypeLevelSepIndex === -1) {
                    // Flat collection at this depth.
                    // sources are the elements
                    data.push([]);
                    const source = { identifiers: identifiers, dataset: elementObject, tags: elementObject.tags };
                    sources.push(source);
                } else {
                    const restCollectionType = collectionType.slice(collectionTypeLevelSepIndex + 1);
                    const elementObj = this.populateElementsFromCollectionDescription(
                        elementObject.elements,
                        restCollectionType,
                        identifiers
                    );
                    const elementData = elementObj.data;
                    const elementSources = elementObj.sources;
                    data = data.concat(elementData);
                    sources = sources.concat(elementSources);
                }
            }
            return { data, sources };
        },
        highlightColumn(n) {
            const headerSelection = $(`.htCore > thead > tr > th:nth-child(${n + 1})`);
            headerSelection.addClass("ht__highlight");
            const bodySelection = $(`.htCore > tbody > tr > td:nth-child(${n + 1})`);
            bodySelection.addClass("rule-highlight");
        },
        unhighlightColumn(n) {
            const headerSelection = $(`.htCore > thead > tr > th:nth-child(${n + 1})`);
            headerSelection.removeClass("ht__highlight");
            const bodySelection = $(`.htCore > tbody > tr > td:nth-child(${n + 1})`);
            bodySelection.removeClass("rule-highlight");
        },
        _datasetFor(dataIndex, data, mappingAsDict) {
            const res = {};
            if (mappingAsDict.url) {
                const urlColumn = mappingAsDict.url.columns[0];
                let url = data[dataIndex][urlColumn];
                if (url.indexOf("://") == -1) {
                    // special case columns containing SRA links. EBI serves these a lot
                    // faster over FTP.
                    if (url.indexOf("ftp.sra.") !== -1) {
                        url = "ftp://" + url;
                    } else {
                        url = "http://" + url;
                    }
                }
                res["url"] = url;
                res["src"] = "url";
            } else if (mappingAsDict.ftp_path) {
                const ftpPathColumn = mappingAsDict.ftp_path.columns[0];
                const ftpPath = data[dataIndex][ftpPathColumn];
                res["ftp_path"] = ftpPath;
                res["src"] = "ftp_import";
            }
            if (mappingAsDict.dbkey) {
                const dbkeyColumn = mappingAsDict.dbkey.columns[0];
                const dbkey = data[dataIndex][dbkeyColumn];
                res["dbkey"] = dbkey;
            } else if (this.genome) {
                res["dbkey"] = this.genome;
            }
            if (mappingAsDict.file_type) {
                const fileTypeColumn = mappingAsDict.file_type.columns[0];
                const fileType = data[dataIndex][fileTypeColumn];
                res["ext"] = fileType;
            } else if (this.extension) {
                res["ext"] = this.extension;
            }
            if (mappingAsDict.name) {
                const nameColumn = mappingAsDict.name.columns[0];
                const name = data[dataIndex][nameColumn];
                res["name"] = name;
            }
            if (mappingAsDict.info) {
                const infoColumn = mappingAsDict.info.columns[0];
                const info = data[dataIndex][infoColumn];
                res["info"] = info;
            }
            const tags = [];
            if (mappingAsDict.tags) {
                const tagColumns = mappingAsDict.tags.columns;
                for (const tagColumn of tagColumns) {
                    const tag = data[dataIndex][tagColumn];
                    tags.push(tag);
                }
            }
            if (mappingAsDict.group_tags) {
                const groupTagColumns = mappingAsDict.group_tags.columns;
                for (const groupTagColumn of groupTagColumns) {
                    const tag = data[dataIndex][groupTagColumn];
                    tags.push("group:" + tag);
                }
            }
            if (mappingAsDict.name_tag) {
                const nameTagColumn = mappingAsDict.name_tag.columns[0];
                const nameTag = data[dataIndex][nameTagColumn];
                tags.push("name:" + nameTag);
            }
            if (tags.length > 0) {
                res["tags"] = tags;
            }
            return res;
        },
    },
    created() {
        if (this.elementsType !== "collection_contents") {
            let columnCount = null;
            if (this.elementsType == "datasets") {
                for (const element of this.initialElements) {
                    if (element.history_content_type == "dataset_collection") {
                        this.errorMessage =
                            "This component can only be used with datasets, you have specified one or more collections.";
                        this.state = "error";
                    }
                }
            } else {
                for (const row of this.initialElements) {
                    if (columnCount == null) {
                        columnCount = row.length;
                    } else {
                        if (columnCount != row.length) {
                            this.jaggedData = true;
                            break;
                        }
                    }
                }
            }

            // TODO: provider...
            UploadUtils.getUploadDatatypes(false, UploadUtils.AUTO_EXTENSION)
                .then((extensions) => {
                    this.extensions = extensions;
                    this.extension = UploadUtils.DEFAULT_EXTENSION;
                })
                .catch((err) => {
                    console.log("Error in RuleCollectionBuilder, unable to load datatypes", err);
                });

            // TODO: provider...
            UploadUtils.getUploadGenomes(UploadUtils.DEFAULT_GENOME)
                .then((genomes) => {
                    this.genomes = genomes;
                    this.genome = UploadUtils.DEFAULT_GENOME;
                })
                .catch((err) => {
                    console.log("Error in RuleCollectionBuilder, unable to load genomes", err);
                });
        }
    },
    watch: {
        addColumnRegexType: function (val) {
            if (val == "groups") {
                this.addColumnRegexGroupCount = 1;
            }
            if (val == "replacement") {
                this.addColumnRegexReplacement = null;
            }
        },
    },
    components: {
        HotTable,
        RuleComponent,
        RuleTargetComponent,
        SavedRulesSelector,
        RuleDisplay,
        IdentifierDisplay,
        ColumnSelector,
        RegularExpressionInput,
        StateDiv,
        RuleModalHeader,
        RuleModalMiddle,
        RuleModalFooter,
        Select2,
    },
};
</script>

<style src="../../node_modules/handsontable/dist/handsontable.full.css"></style>
<style>
.table-column {
    width: 100%;
    overflow: hidden;
}
.select2-container {
    min-width: 60px;
}
.vertical #hot-table {
    width: 100%;
    overflow: hidden;
    height: 400px;
}
.horizontal #hot-table {
    width: 100%;
    overflow: hidden;
    height: 250px;
}
.rule-builder-body {
    height: 400px;
}
.rule-column.vertical {
    height: 400px;
}
.rule-column.horizontal {
    height: 150px;
}
.rules-container-full {
    width: 100%;
    height: 400px;
}
.rules-container {
    border: 1px dashed #ccc;
    padding: 5px;
}
.rules-container-vertical {
    width: 300px;
    height: 400px;
}
.rules-container-horizontal {
    width: 100%;
    height: 150px;
}
.rules-container .title {
    font-weight: bold;
}
.rule-summary {
    height: 100%;
    display: flex;
    flex-direction: column;
}
.rule-edit-buttons {
    margin: 5px;
}
.rules {
    flex-grow: 1;
    overflow-y: scroll;
}
.rule-source {
    height: 400px;
}
.rules li {
    list-style-type: circle;
    list-style-position: inside;
    padding: 5px;
    padding-top: 0px;
    padding-bottom: 0px;
}
.rule-column-selector li {
    list-style-type: circle;
    list-style-position: inside;
    padding: 5px;
    padding-top: 0px;
    padding-bottom: 0px;
}
.rules .rule-error {
    display: block;
    margin-left: 10px;
    font-style: italic;
    color: red;
}
.rule-warning {
    display: block;
    margin-left: 10px;
    font-style: italic;
    color: #e28809;
}
.rule-summary .title {
    font-size: 1.1em;
}
.rule-highlight {
    font-style: italic;
    font-weight: bold;
}
.rules-buttons {
}
.rule-footer-inputs label {
    padding-left: 20px;
    align-self: baseline;
}
.rule-footer-inputs .select2-container {
    align-self: baseline;
}
.rule-footer-inputs {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    align-items: baseline;
}
.rule-footer-inputs input {
    align-self: baseline;
}
.extension-select {
    flex: 1;
    max-width: 120px;
    min-width: 60px;
}
.genome-select {
    flex: 1;
    max-width: 300px;
    min-width: 120px;
}
.collection-name {
    flex: 1;
    min-width: 120px;
    max-width: 500px;
}
.rule-footer-genome-group {
    flex: 2;
    display: flex;
}
.rule-footer-extension-group {
    flex: 1;
    display: flex;
}
.rule-footer-name-group {
    flex: 3;
    display: flex;
    flex-direction: row-reverse;
}
.fa-edit,
.fa-times,
.fa-wrench {
    cursor: pointer;
}
.fa-history {
    cursor: pointer;
}
</style>
