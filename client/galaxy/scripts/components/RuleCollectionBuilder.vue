<template>
    <state-div v-if="state == 'build'">
        <!-- Different instructions if building up from individual datasets vs. 
             initial data import. -->
        <div class="header flex-row no-flex" v-if="ruleView == 'source'">
            The is an advanced setting, below is a raw JSON description of the rules to apply to the tabular data used. The alternative graphical editor is recommended for most usages.
        </div>
        <div class="header flex-row no-flex" v-else-if="elementsType == 'datasets'">
            Use this form to describe rules for building a collection from the specified datasets.
        </div>
        <!-- This modality allows importing individual datasets, multiple collections,
             and requires a data source - note that. -->
        <div class="header flex-row no-flex" v-else-if="importType == 'datasets'">
            Use this form to describe rules for import datasets. At least one column should be defined to a source to fetch data from (URLs, FTP files, etc...).
        </div>
        <div class="header flex-row no-flex" v-else>
            Use this form to describe rules for import datasets. At least one column should be defined to a source to fetch data from (URLs, FTP files, etc...). Be sure to specify at least one column as a list identifier - specify more to created nested list structures. Specify a column to serve as "collection name" to group datasets into multiple collections.
        </div>
        <div class="middle flex-row flex-row-container" v-if="ruleView == 'source'">
            <p class="alert-message" v-if="ruleSourceError">{{ ruleSourceError }}</p>
            <textarea class="rule-source" v-model="ruleSource"></textarea>
        </div>
        <div class="middle flex-row flex-row-container" v-else>
            <!-- column-headers -->
            <div class="rule-builder-body vertically-spaced"
                 v-bind:class="{ 'flex-column-container': vertical }" v-if="ruleView == 'normal'">
                <!-- width: 30%; -->
                <div class="rule-column" v-bind:class="orientation">
                    <div class="rules-container" v-bind:class="{'rules-container-vertical': vertical, 'rules-container-horizontal': horizontal}">
                        <rule-component rule-type="sort"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addSortingTarget" :col-headers="activeRuleColHeaders" />
                            <label :title="titleNumericSort">
                                <input type="checkbox" v-model="addSortingNumeric" />
                                {{ l("Numeric sorting.") }}
                            </label>
                        </rule-component>
                        <rule-component rule-type="add_column_basename"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addColumnBasenameTarget" :col-headers="activeRuleColHeaders" />
                        </rule-component>
                        <rule-component rule-type="add_column_rownum"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <label>
                                {{ l("Starting from") }}
                                <input type="number" v-model="addColumnRownumStart" min="0" />
                            </label>
                        </rule-component>
                        <rule-component rule-type="add_column_regex"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addColumnRegexTarget" :col-headers="activeRuleColHeaders" />
                            <input type="radio" v-model="addColumnRegexType" value="global">Create column matching expression.<br />
                            <input type="radio" v-model="addColumnRegexType" value="groups">Create columns matching expression groups.<br />
                            <input type="radio" v-model="addColumnRegexType" value="replacement">Create column from expression replacement.<br />
                            <regular-expression-input :target.sync="addColumnRegexExpression" />
                            <label v-if="addColumnRegexType=='groups'">
                                {{ l("Number of Groups") }}
                                <input type="number" v-model="addColumnRegexGroupCount" min="1" />
                            </label>
                            <label v-if="addColumnRegexType=='replacement'">
                                {{ l("Replacement Expression") }}
                                <input type="text" v-model="addColumnRegexReplacement" class="rule-replacement" />
                            </label>
                        </rule-component>
                        <rule-component rule-type="add_column_concatenate"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addColumnConcatenateTarget0" :col-headers="activeRuleColHeaders" />
                            <column-selector :target.sync="addColumnConcatenateTarget1" :col-headers="activeRuleColHeaders" />
                        </rule-component>
                        <rule-component rule-type="add_column_substr"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
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
                        <rule-component rule-type="add_column_value"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <label>
                                {{ l("Value") }}
                                <input type="text" v-model="addColumnValue" />
                            </label>
                        </rule-component>
                        <rule-component rule-type="remove_columns"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="removeColumnTargets" :col-headers="activeRuleColHeaders" :multiple="true" />
                        </rule-component>
                        <rule-component rule-type="split_columns"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="splitColumnsTargets0" label="Odd Row Column(s)" :col-headers="activeRuleColHeaders" :multiple="true" />
                            <column-selector :target.sync="splitColumnsTargets1" label="Even Row Column(s)" :col-headers="activeRuleColHeaders" :multiple="true" />
                        </rule-component>
                        <rule-component rule-type="swap_columns"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="swapColumnsTarget0" label="Swap Column" :col-headers="activeRuleColHeaders" />
                            <column-selector :target.sync="swapColumnsTarget1" label="With Column" :col-headers="activeRuleColHeaders" />
                        </rule-component>
                        <rule-component rule-type="add_filter_regex"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addFilterRegexTarget" :col-headers="activeRuleColHeaders" />
                            <regular-expression-input :target.sync="addFilterRegexExpression" />
                            <label :title="titleInvertFilterRegex">
                                <input type="checkbox" v-model="addFilterRegexInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <rule-component rule-type="add_filter_matches"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addFilterMatchesTarget" :col-headers="activeRuleColHeaders" />
                            <input type="text" v-model="addFilterMatchesValue" />
                            <label :title="titleInvertFilterMatches">
                                <input type="checkbox" v-model="addFilterMatchesInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <rule-component rule-type="add_filter_compare"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addFilterCompareTarget" :col-headers="activeRuleColHeaders" />
                            <label>
                                Filter out rows
                                <select v-model="addFilterCompareType">
                                    <option value="less_than">{{ l("less than") }} </option>
                                    <option value="less_than_equal">{{ l("less than or equal to") }}</option>
                                    <option value="greater_than">{{ l("greater than") }}</option>
                                    <option value="greater_than_equal">{{ l("greater than or equal to") }}</option>
                                </select>
                            </label>
                            <input type="text" v-model="addFilterCompareValue" />
                        </rule-component>
                        <rule-component rule-type="add_filter_count"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
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
                            <label :title="titleInvertFilterMatches">
                                <input type="checkbox" v-model="addFilterCountInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <rule-component rule-type="add_filter_empty"
                                        :display-rule-type="displayRuleType"
                                        :builder="this">
                            <column-selector :target.sync="addFilterEmptyTarget" :col-headers="activeRuleColHeaders" />
                            <label :title="titleInvertFilterEmpty">
                                <input type="checkbox" v-model="addFilterEmptyInvert" />
                                {{ l("Invert filter.") }}
                            </label>
                        </rule-component>
                        <div v-if="displayRuleType == 'mapping'">
                            <div class="map"
                                 v-for="map in mapping"
                                 v-bind:index="map.index"
                                 v-bind:key="map.type">
                                <column-selector 
                                    :class="'rule-map-' + map.type.replace(/_/g, '-')"
                                    :label="mappingTargets()[map.type].label"
                                    :target.sync="map.columns"
                                    :ordered-edit.sync="map.editing"
                                    :col-headers="colHeaders"
                                    :multiple="mappingTargets()[map.type].multiple"
                                    :ordered="true"
                                    :value-as-list="true" />
                            </div>
                            <div class="buttons">
                                <div class="btn-group" v-if="unmappedTargets.length > 0">
                                  <button type="button" class="primary-button dropdown-toggle" data-toggle="dropdown">
                                    <span class="fa fa-plus rule-add-mapping"></span> {{ "Add Definition" }}<span class="caret"></span>
                                  </button>
                                  <ul class="dropdown-menu" role="menu">
                                    <li v-for="target in unmappedTargets"
                                        v-bind:index="target"
                                        v-bind:key="target">
                                      <a :class="'rule-add-mapping-' + target.replace(/_/g, '-')" @click="addIdentifier(target)">{{ mappingTargets()[target].label }}</a>
                                    </li>
                                  </ul>
                                </div>
                               <button type="button" class="ui-button-default btn btn-default rule-mapping-ok" v-if="!hasActiveMappingEdit" @click="displayRuleType = null">Okay</button>
                            </div>
                        </div>
                        <div class="rule-summary" v-if="displayRuleType == null">
                            <span class="title">
                                {{ l("Rules") }}
                                <span class="fa fa-wrench rule-builder-view-source" :title="titleViewSource" @click="viewSource"></span>
                            </span>
                            <div v-if="jaggedData" class="rule-warning">
                                Rows contain differing numbers of columns, there was likely a problem parsing your data.
                            </div>
                            <ol class="rules">
                                <!-- Example at the end of https://vuejs.org/v2/guide/list.html -->
                                <rule-display
                                  v-for="(rule, index) in rules"
                                  v-bind:rule="rule"
                                  v-bind:index="index"
                                  v-bind:key="index"
                                  @edit="editRule(rule, index)"
                                  @remove="removeRule(index)"
                                  :col-headers="colHeadersPerRule[index]" />
                                <identifier-display v-for="(map, index) in mapping"
                                                    v-bind="map"
                                                    v-bind:index="index"
                                                    v-bind:key="map.type"
                                                    @remove="removeMapping(index)"
                                                    @edit="displayRuleType = 'mapping'"
                                                    v-on:mouseover.native="map.columns.forEach((col) => highlightColumn(col))"
                                                    v-on:mouseout.native="map.columns.forEach((col) =>unhighlightColumn(col))"
                                                    :col-headers="colHeaders" />
                                <div v-if="mapping.length == 0">
                                    One or more column definitions must be specified. These are required to specify how to build collections and datasets from rows and columns of the table. <a href="#" @click="displayRuleType = 'mapping'">Click here</a> to manage column definitions.
                                </div>
                            </ol>
                            <div class="rules-buttons">
                                <div class="btn-group dropup">
                                  <button type="button" class="rule-menu-rules-button primary-button dropdown-toggle" data-toggle="dropdown">
                                    <span class="fa fa-plus"></span> {{ l("Rules") }}<span class="caret"></span>
                                  </button>
                                  <ul class="dropdown-menu" role="menu">
                                    <rule-target-component :builder="this" rule-type="sort" />
                                    <rule-target-component :builder="this" rule-type="remove_columns" />
                                    <rule-target-component :builder="this" rule-type="split_columns" />
                                    <rule-target-component :builder="this" rule-type="swap_columns" />
                                    <li><a class="rule-link rule-link-mapping" @click="displayRuleType = 'mapping'">Add / Modify Column Definitions</a></li>
                                  </ul>
                                </div>
                                <div class="btn-group dropup">
                                    <button type="button" class="rule-menu-filter-button primary-button dropdown-toggle" data-toggle="dropdown">
                                        <span class="fa fa-plus"></span> {{ l("Filter") }}<span class="caret"></span>
                                    </button>
                                    <ul class="dropdown-menu" role="menu">
                                        <rule-target-component :builder="this" rule-type="add_filter_regex" />
                                        <rule-target-component :builder="this" rule-type="add_filter_matches" />
                                        <rule-target-component :builder="this" rule-type="add_filter_compare" />
                                        <rule-target-component :builder="this" rule-type="add_filter_empty" />
                                        <rule-target-component :builder="this" rule-type="add_filter_count" />
                                  </ul>
                                </div>
                                <div class="btn-group dropup">
                                    <button type="button" class="rule-menu-column-button primary-button dropdown-toggle" data-toggle="dropdown">
                                        <span class="fa fa-plus"></span> {{ l("Column") }}<span class="caret"></span>
                                    </button>
                                    <ul class="dropdown-menu" role="menu">
                                        <rule-target-component :builder="this" rule-type="add_column_basename" />
                                        <rule-target-component :builder="this" rule-type="add_column_regex" />
                                        <rule-target-component :builder="this" rule-type="add_column_concatenate" />
                                        <rule-target-component :builder="this" rule-type="add_column_rownum" />
                                        <rule-target-component :builder="this" rule-type="add_column_value" />
                                        <rule-target-component :builder="this" rule-type="add_column_substr" />
                                  </ul>
                                </div> 
                            </div>                               
                        </div>
                    </div>
                </div>
                <!--  flex-column column -->
                <!--  style="width: 70%;" -->
                <div class="table-column" v-bind:class="orientation" style="width: 100%;">
                    <hot-table id="hot-table"
                               ref="hotTable"
                               :data="hotData['data']"
                               :colHeaders="colHeadersDisplay"
                               :readOnly="true"
                               stretchH="all">
                    </hot-table>
                </div>
            </div>
        </div>
        <div class="footer flex-row no-flex vertically-spaced" v-if="ruleView == 'source'">
            <option-buttons-div>
                <button @click="resetSource" class="creator-reset-btn btn rule-btn-reset">
                    {{ l("Reset") }}
                </button>
               <button @click="attemptRulePreview" class="btn btn-primary rule-btn-okay">
                    {{ l("Okay")}}
                </button>
            </option-buttons-div>
        </div>
        <div class="footer flex-row no-flex vertically-spaced"
             v-else-if="ruleView == 'normal'">
            <div class="attributes clear"/>
            <label class="rule-option" v-if="elementsType == 'datasets'">
                {{ l("Hide original elements") }}:
                <input type="checkbox" v-model="hideSourceItems" />
            </label>
            <label class="rule-option rule-option-extension" v-if="elementsType !== 'datasets' && !mappingAsDict.file_type">
                {{ l("Type") }}:
                <select2 name="extension" style="width: 120px" v-model="extension" v-if="extension">
                    <option v-for="(col, index) in extensions" :value="col['id']"">{{ col["text"] }}</option>
                </select2>
            </label>
            <label class="rule-option" v-if="elementsType !== 'datasets' && !mappingAsDict.dbkey">
                {{ l("Genome") }}:
                <select2 id="genome-selector" style="width: 120px" v-model="genome" v-if="genome">
                    <option v-for="(col, index) in genomes" :value="col['id']"">{{ col["text"] }}</option>
                </select2>
            </label>
            <label class="rule-option pull-right" v-if="mappingAsDict.list_identifiers && !mappingAsDict.collection_name">
                {{ l("Name") }}:
                <input class="collection-name" style="width: 260px" 
                :placeholder="namePlaceholder" v-model="collectionName" />
            </label>
            <option-buttons-div>
                <button @click="swapOrientation" class="creator-orient-btn btn rule-btn-reorient" tabindex="-1">
                    {{ l("Re-orient") }}
                </button>
                <button @click="cancel" class="creator-cancel-btn btn rule-btn-cancel" tabindex="-1">
                    {{ l("Cancel") }}
                </button>
                <button @click="resetRulesAndState" :title="titleReset" class="creator-reset-btn btn rule-btn-reset">
                    {{ l("Reset") }}
                </button>
                <button @click="createCollection" class="create-collection btn btn-primary rule-btn-okay" v-bind:class="{ disabled: !validInput }">
                    {{ elementsType == "datasets" ? l("Create") : l("Upload") }}
                </button>
            </option-buttons-div>
        </div>
    </state-div>
    <state-div v-else-if="state == 'wait'">
        <div class="header flex-row no-flex">
            {{ l("Galaxy is waiting for collection creation, this dialog will close when this is complete.") }}
        </div>
        <div class="footer flex-row no-flex">
            <option-buttons-div>
                <button @click="cancel" class="creator-cancel-btn btn" tabindex="-1">
                    {{ l("Close") }}
                </button>
            </option-buttons-div>
        </div>
    </state-div>
    <state-div v-else-if="state == 'error'">
        <!-- TODO: steal styling from paired collection builder warning... -->
        <div>
            {{ errorMessage }}
        </div>
    </state-div>
</template>
<script>
import axios from "axios";
import _l from "utils/localization";
import HotTable from 'vue-handsontable-official';
import Popover from "mvc/ui/ui-popover";
import UploadUtils from "mvc/upload/upload-utils";
import JobStatesModel from "mvc/history/job-states-model";
import Vue from "vue";


const MAPPING_TARGETS = {
    list_identifiers: {
        multiple: true,
        label: _l("List Identifier(s)"),
        columnHeader: _l("List Identifier"),
        help: _l("This should be a short description of the replicate, sample name, condition, etc... that describes each level of the list structure."),
        importType: "collections",
    },
    paired_identifier: {
        label: _l("Paired-end Indicator"),
        columnHeader: _l("Paired Indicator"),
        help: _l("This should be set to '1', 'R1', 'forward', 'f', or 'F' to indicate forward reads, and '2', 'r', 'reverse', 'R2', 'R', or 'R2' to indicate reverse reads."),
        importType: "collections",
    },
    collection_name: {
        label: _l("Collection Name"),
        help: _l("If this is set, all rows with the same collection name will be joined into a collection and it is possible to create multiple collections at once."),
        modes: ["raw", "ftp"],  // TODO: allow this in datasets mode.
        importType: "collections",
    },
    name: {
        label: _l("Name"),
        importType: "datasets",
    },
    dbkey: {
        label: _l("Genome"),
        modes: ["raw", "ftp"],
    },
    file_type: {
        label: _l("Type"),
        modes: ["raw", "ftp"],
        help: _l("This should be the Galaxy file type corresponding to this file."),
    },
    url: {
        label: _l("URL"),
        modes: ["raw"],
        help: _l("This should be a URL the file can be downloaded from."),
    },
    info: {
        label: _l("Info"),
        help: _l("Unstructured text associated with the dataset that shows up in the history panel, this is optional and can be whatever you would like."),
        modes: ["raw", "ftp"],
    },
    ftp_path: {
        label: _l("FTP Path"),
        modes: ["raw", "ftp"],
        help: _l("This should be the path to the target file to include relative to your FTP directory on the Galaxy server"),
        requiresFtp: true,
    }
}

const applyRegex = function(regex, target, data, replacement, groupCount) {
    let regExp;
    try {
        regExp = RegExp(regex);
    } catch(error) {
        return {error: `Invalid regular expression specified.`};
    }
    let failedCount = 0;
    function newRow(row) {
        const source = row[target];
        if (!replacement) {
            const match = regExp.exec(source);
            if(!match) {
              failedCount++;
              return null;
            }
            groupCount = groupCount && parseInt(groupCount);
            if(groupCount) {
                if(match.length != (groupCount + 1)) {
                    failedCount++;
                    return null;
                }
                return row.concat(match.splice(1, match.length));
            } else {
                return row.concat([match[0]]);
            }
        } else {
            return row.concat([source.replace(regExp, replacement)]);
        }
    }
    data = data.map(newRow);
    if(failedCount > 0) {
        return {error: `${failedCount} row(s) failed to match specified regular expression.`};
    }
    return {data};
}

const multiColumnsToString = function(targetColumns, colHeaders) {
    if (targetColumns.length == 0) {
        return `no columns`;
    } else if (targetColumns.length == 1) {
        return `column ${colHeaders[targetColumns[0]]}`;
    } else {
        const targetHeaders = targetColumns.map((el) => colHeaders[el]);
        // https://stackoverflow.com/questions/16251822/array-to-comma-separated-string-and-for-last-tag-use-the-and-instead-of-comma
        return `columns ${[targetHeaders.slice(0, -1).join(', '), targetHeaders.slice(-1)[0]].join(' and ')}`;
    }
}

const Rules = {
    add_column_basename: {
        title: _l("Basename of Path of URL"),
        display: (rule, colHeaders) => {
          return `Add column using basename of column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addColumnBasenameTarget = 0;
            } else {
                component.addColumnBasenameTarget = rule.target_column;
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addColumnBasenameTarget;
        },
        apply: (rule, data, sources) => {
            // https://github.com/kgryte/regex-basename-posix/blob/master/lib/index.js
            //const re = /^(?:\/?|)(?:[\s\S]*?)((?:\.{1,2}|[^\/]+?|)(?:\.[^.\/]*|))(?:[\/]*)$/;
            // https://stackoverflow.com/questions/8376525/get-value-of-a-string-after-a-slash-in-javascript
            const re = /[^/]*$/;
            const target = rule.target_column;
            return applyRegex(re, target, data);
        }
    },
    add_column_rownum: {
        title: _l("Row Number"),
        display: (rule, colHeaders) => {
          return `Add column for the current row number.`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addColumnRownumStart = 1;
            } else {
                component.addColumnRownumStart = rule.start;
            }
        },
        save: (component, rule) => {
            rule.start = component.addColumnRownumStart;
        },
        apply: (rule, data, sources) => {
          let rownum = rule.start;
          function newRow(row) {
            const newRow = row.slice();
            newRow.push(rownum);
            rownum += 1;
            return newRow;
          }
          data = data.map(newRow);
          return {data};
        }
    },
    add_column_value: {
        title: _l("Fixed Value"),
        display: (rule, colHeaders) => {
          return `Add column for the constant value of ${rule.value}.`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addColumnValue = "";
            } else {
                component.addColumnValue = rule.value;
            }
        },
        save: (component, rule) => {
            rule.value = component.addColumnValue;
        },
        apply: (rule, data, sources) => {
          const addValue = rule.value;
          function newRow(row) {
            const newRow = row.slice();
            newRow.push(addValue);
            return newRow;
          }
          data = data.map(newRow);
          return {data};
        }
    },
    add_column_regex: {
        title: _l("Using a Regular Expression"),
        display: (rule, colHeaders) => {
          return `Add new column using ${rule.expression} applied to column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addColumnRegexTarget = 0;
                component.addColumnRegexExpression = "";
                component.addColumnRegexReplacement = null;
                component.addColumnRegexGroupCount = null;
            } else {
                component.addColumnRegexTarget = rule.target_column;
                component.addColumnRegexExpression = rule.expression;
                component.addColumnRegexReplacement = rule.replacement;
                component.addColumnRegexGroupCount = rule.group_count;
            }
            let addColumnRegexType = "global";
            if(component.addColumnRegexGroupCount) {
                addColumnRegexType = "groups";
            } else if (component.addColumnRegexReplacement) {
                addColumnRegexType = "replacement";
            }
            component.addColumnRegexType = addColumnRegexType;
        },
        save: (component, rule) => {
            rule.target_column = component.addColumnRegexTarget;
            rule.expression = component.addColumnRegexExpression;
            if(component.addColumnRegexReplacement) {
                rule.replacement = component.addColumnRegexReplacement;
            }
            if(component.addColumnRegexGroupCount) {
                rule.group_count = component.addColumnRegexGroupCount;
            }
        },
        apply: (rule, data, sources) => {
          const target = rule.target_column;
          return applyRegex(rule.expression, target, data, rule.replacement, rule.group_count);
        }
    },
    add_column_concatenate: {
        title: _l("Concatenate Columns"),
        display: (rule, colHeaders) => {
          return `Concatenate column ${colHeaders[rule.target_column_0]} and column ${colHeaders[rule.target_column_1]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addColumnConcatenateTarget0 = 0;
                component.addColumnConcatenateTarget1 = 0;
            } else {
                component.addColumnConcatenateTarget0 = rule.target_column_0;
                component.addColumnConcatenateTarget1 = rule.target_column_1;
            }
        },
        save: (component, rule) => {
            rule.target_column_0 = component.addColumnConcatenateTarget0;
            rule.target_column_1 = component.addColumnConcatenateTarget1;
        },
        apply: (rule, data, sources) => {
          const target0 = rule.target_column_0;
          const target1 = rule.target_column_1;
          function newRow(row) {     
            const newRow = row.slice();
            newRow.push(row[target0] + row[target1]);
            return newRow;
          }
          data = data.map(newRow);
          return {data};
        }       
    },
    add_column_substr: {
        title: _l("Keep or Trim Prefix or Suffix"),
        display: (rule, colHeaders) => {
          const type = rule.substr_type;
          let display;
          if(type == "keep_prefix") {
              display = `Keep only ${rule.length} characters from the start of column ${colHeaders[rule.target_column]}`
          } else if(type == "drop_prefix") {
              display = `Remove ${rule.length} characters from the start of column ${colHeaders[rule.target_column]}`;
          } else if(type == "keep_suffix") {
              display = `Keep only ${rule.length} characters from the end of column ${colHeaders[rule.target_column]}`
          } else {
              display = `Remove ${rule.length} characters from the end of column ${colHeaders[rule.target_column]}`;
          }
          return display;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addColumnSubstrTarget = 0;
                component.addColumnSubstrType = "keep_prefix";
                component.addColumnSubstrLength = 1;
            } else {
                component.addColumnSubstrTarget = rule.target_column;
                component.addColumnSubstrLength = rule.length;
                component.addColumnSubstrType = rule.substr_type;
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addColumnSubstrTarget;
            rule.length = component.addColumnSubstrLength;
            rule.substr_type = component.addColumnSubstrType;
        },
        apply: (rule, data, sources) => {
          const target = rule.target_column;
          const length = rule.length;
          const type = rule.substr_type;
          function newRow(row) {
            const newRow = row.slice();
            const originalValue = row[target];
            let start = 0, end = originalValue.length;
            if(type == "keep_prefix") {
                end = length;
            } else if(type == "drop_prefix") {
                start = length;
            } else if(type == "keep_suffix") {
                start = end - length;
                if(start < 0) {
                    start = 0;
                }
            } else {
                end = end - length;
                if(end < 0) {
                    end = 0;
                }
            }
            newRow.push(originalValue.substr(start, end));
            return newRow;
          }
          data = data.map(newRow);
          return {data};
        }       
    },
    remove_columns: {
        title: _l("Remove Column(s)"),
        display: (rule, colHeaders) => {
            const targetColumns = rule.target_columns;
            return `Remove ${multiColumnsToString(targetColumns, colHeaders)}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.removeColumnTargets = [];
            } else {
                component.removeColumnTargets = rule.target_columns;
            }
        },
        save: (component, rule) => {
            rule.target_columns = component.removeColumnTargets;
        },
        apply: (rule, data, sources) => {
          const targets = rule.target_columns;
          function newRow(row) {
            const newRow = []
            for(let index in row) {
              if(targets.indexOf(parseInt(index)) == -1) {
                newRow.push(row[index]);
              }
            }
            return newRow;
          }
          data = data.map(newRow);
          return {data};
        }
    },
    add_filter_regex: {
        title: _l("Using a Regular Expression"),
        display: (rule, colHeaders) => {
            return `Filter rows using regular expression ${rule.expression} on column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addFilterRegexTarget = 0;
                component.addFilterRegexExpression = "";
                component.addFilterRegexInvert = false;
            } else {                
               component.addFilterRegexTarget = rule.target_column;
               component.addFilterRegexExpression = rule.expression;
               component.addFilterRegexInvert = rule.invert;               
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addFilterRegexTarget;
            rule.expression = component.addFilterRegexExpression;
            rule.invert = component.addFilterRegexInvert;
        },
        apply: (rule, data, sources) => {
          try {
              regExp = RegExp(regex);
          } catch(error) {
              return {error: `Invalid regular expression specified.`};
          }
          const target = rule.target_column;
          const invert = rule.invert;
          const filterFunction = function(el, index) {
              const row = data[parseInt(index)];
              return regExp.exec(row[target]) ? !invert : invert;
          }
          sources = sources.filter(filterFunction);
          data = data.filter(filterFunction);
          return {data, sources};
        }
    },
    add_filter_count: {
        title: _l("First or Last N Rows"),
        display: (rule, colHeaders) => {
            const which = rule.which;
            const invert = rule.invert;
            if(which == "first" && ! invert) {
                return `Filter out first ${rule.count} row(s).}`;            
            } else if(which == "first" && invert) {
                return `Keep only first ${rule.count} row(s).}`;            
            } else if(which == "last" && ! invert) {
                return `Filter out last ${rule.count} row(s).}`;
            } else {
                return `Keep only last ${rule.count} row(s).}`;
            }
        },
        init: (component, rule) => {
            if(!rule) {
                component.addFilterCountN = 0;
                component.addFilterCountWhich = "first";
                component.addFilterCountInvert = false;
            } else {
                component.addFilterCountN = rule.count;
                component.addFilterCountWhich = rule.which;
                component.addFilterCountInvert = rule.inverse;
            }
        },
        save: (component, rule) => {
            rule.count = component.addFilterCountN;
            rule.which = component.addFilterCountWhich;
            rule.invert = component.addFilterCountInvert;
        },
        apply: (rule, data, sources) => {
          const count = rule.count;
          const invert = rule.invert;
          const which = rule.which;
          const dataLength = data.length;
          const filterFunction = function(el, index) {
              let matches;
              if(which == "first") {
                  matches = index >= count;
              } else {
                  matches = index < (dataLength - count);
              }
              return matches ? !invert : invert;
          }
          sources = sources.filter(filterFunction);
          data = data.filter(filterFunction);
          return {data, sources};
        }
    },
    add_filter_empty: {
        title: _l("On Emptiness"),
        display: (rule, colHeaders) => {
            return `Filter rows if no value for column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addFilterEmptyTarget = 0;
                component.addFilterEmptyInvert = false;
            } else {
               component.addFilterEmptyTarget = rule.target_column;
               component.addFilterEmptyInvert = rule.invert;
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addFilterEmptyTarget;
            rule.invert = component.addFilterEmptyInvert;
        },
        apply: (rule, data, sources) => {
          const target = rule.target_column;
          const invert = rule.invert;
          const filterFunction = function(el, index) {
              const row = data[parseInt(index)];
              return row[target].length ? !invert : invert;
          }
          sources = sources.filter(filterFunction);
          data = data.filter(filterFunction);
          return {data, sources};
        }
    },
    add_filter_matches: {
        title: _l("Matching a Supplied Value"),
        display: (rule, colHeaders) => {
            return `Filter rows with value ${rule.value} for column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addFilterMatchesTarget = 0;
                component.addFilterMatchesValue = "";
                component.addFilterMatchesInvert = false;
            } else {                
               component.addFilterMatchesTarget = rule.target_column;
               component.addFilterMatchesValue = rule.value;
               component.addFilterMatchesInvert = rule.invert;               
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addFilterMatchesTarget;
            rule.value = component.addFilterMatchesValue;
            rule.invert = component.addFilterMatchesInvert;
        },
        apply: (rule, data, sources) => {
          const target = rule.target_column;
          const invert = rule.invert;
          const value = rule.value;
          const filterFunction = function(el, index) {
              const row = data[parseInt(index)];
              return row[target] == value ? !invert : invert;
          }
          sources = sources.filter(filterFunction);
          data = data.filter(filterFunction);
          return {data, sources};
        }
    },
    add_filter_compare: {
        title: _l("By Comparing to a Numeric Value"),
        display: (rule, colHeaders) => {
            return `Filter rows with value ${rule.compare_type} ${rule.value} for column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addFilterCompareTarget = 0;
                component.addFilterCompareValue = 0;
                component.addFilterCompareType = "less_than";
            } else {                
               component.addFilterCompareTarget = rule.target_column;
               component.addFilterCompareValue = rule.value;
               component.addFilterCompareType = rule.compare_type;               
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addFilterCompareTarget;
            rule.value = component.addFilterCompareValue;
            rule.compare_type = component.addFilterCompareType;
        },
        apply: (rule, data, sources) => {
          const target = rule.target_column;
          const compare_type = rule.compare_type;
          const value = rule.value;
          const filterFunction = function(el, index) {
              const row = data[parseInt(index)];
              const targetValue = parseFloat(row[target]);
              let matches;
              if(compare_type == "less_than") {
                matches = targetValue < value;
              } else if(compare_type == "less_than_equal") {
                matches = targetValue <= value;
              } else if(compare_type == "greater_than") {
                matches = targetValue > value;
              } else if(compare_type == "greater_than_equal") {
                matches = targetValue >= value;
              }
              return matches;
          }
          sources = sources.filter(filterFunction);
          data = data.filter(filterFunction);
          return {data, sources};
        }
    },
    sort: {
        title: _l("Sort"),
        display: (rule, colHeaders) => {
            return `Sort on column ${colHeaders[rule.target_column]}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.addSortingTarget = 0;
                component.addSortingNumeric = false;
            } else {                
               component.addSortingTarget = rule.target_column;
               component.addSortingNumeric = rule.numeric;
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addSortingTarget;
            rule.numeric = component.addSortingNumeric;
        },
        apply: (rule, data, sources) => {
          const target = rule.target_column;
          const numeric = rule.numeric;

          const sortable = _.zip(data, sources);

          const sortFunc = (a, b) => {
            let aVal = a[0][target];
            let bVal = b[0][target];
            if(numeric) {
              aVal = parseFloat(aVal);
              bVal = parseFloat(bVal);
            }
            if(aVal < bVal) {
              return -1;
            } else if(bVal < aVal) {
              return 1;
            } else {
              return 0;
            }
          }

          sortable.sort(sortFunc);

          const newData = [];
          const newSources = [];

          sortable.map((zipped) => { newData.push(zipped[0]); newSources.push(zipped[1]); });

          return {data: newData, sources: newSources};
        }
    },
    swap_columns: {
        title: _l("Swap Column(s)"),        
        display: (rule, colHeaders) => {
            return `Swap ${multiColumnsToString([rule.target_column_0, rule.target_column_1], colHeaders)}`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.swapColumnsTarget0 = 0;
                component.swapColumnsTarget1 = 0;
            } else {
                component.swapColumnsTarget0 = rule.target_column_0;
                component.swapColumnsTarget1 = rule.target_column_1;
            }
        },
        save: (component, rule) => {
            rule.target_column_0 = component.swapColumnsTarget0;
            rule.target_column_1 = component.swapColumnsTarget1;
        },
        apply: (rule, data, sources) => {
          const target0 = rule.target_column_0;
          const target1 = rule.target_column_1;
          function newRow(row) {     
            const newRow = row.slice();
            newRow[target0] = row[target1];
            newRow[target1] = row[target0];
            return newRow;
          }
          data = data.map(newRow);
          return {data};
        }
    },
    split_columns: {
        title: _l("Split Column(s)"),
        display: (rule, colHeaders) => {
            return `Duplicate each row and split up columns`;
        },
        init: (component, rule) => {
            if(!rule) {
                component.splitColumnsTargets0 = [];
                component.splitColumnsTargets1 = [];
            } else {
                component.splitColumnsTargets0 = rule.target_columns_0;
                component.splitColumnsTargets1 = rule.target_columns_1;
            }
        },
        save: (component, rule) => {
            rule.target_columns_0 = component.splitColumnsTargets0;
            rule.target_columns_1 = component.splitColumnsTargets1;
        },
        apply: (rule, data, sources) => {
            const targets0 = rule.target_columns_0;
            const targets1 = rule.target_columns_1;

            const splitRow = function(row) {
                const newRow0 = [], newRow1 = [];
                for(let index in row) {
                    index = parseInt(index);
                    if(targets0.indexOf(index) > -1) {
                        newRow0.push(row[index]);
                    } else if(targets1.indexOf(index) > -1) {
                        newRow1.push(row[index]);
                    } else {
                        newRow0.push(row[index]);
                        newRow1.push(row[index]);
                    }
                }
                return [newRow0, newRow1];
            }

            data = flatMap(splitRow, data);
            sources = flatMap((src) => [src, src], data);
            return {data, sources};
        }
    }
}


// Local components...

// Based on https://vuejs.org/v2/examples/select2.html but adapted to handle list values
// with "multiple: true" set.
const Select2 = {
  props: ['options', 'value', 'placeholder'],
  template: `<select>
    <slot></slot>
  </select>`,
  mounted: function () {
    var vm = this
    $(this.$el)
      // init select2
      .select2({ data: this.options, placeholder: this.placeholder, allowClear: this.placeholder })
      .val(this.value)
      .trigger('change')
      // emit event on change.
      .on('change', function (event) {
        vm.$emit('input', event.val);
      })
  },
  watch: {
    value: function (value) {
      // update value
      $(this.$el).val(value)
    },
    options: function (options) {
      // update options
      $(this.$el).empty().select2({ data: options })
    }
  },
  destroyed: function () {
    $(this.$el).off().select2('destroy')
  }
};


const ColumnSelector = {
    template: `
        <div class="rule-column-selector" v-if="!multiple || !ordered">
            <label>
                {{ label }}
                <select2 :value="target" @input="handleInput" :multiple="multiple">
                    <option v-for="(col, index) in colHeaders" :value="index">{{ col }}</option>
                </select2>
            </label>
        </div>
        <div class="rule-column-selector" v-else>
            {{ label }} 
            <ol>
                <li v-for="(targetEl, index) in target"
                    v-bind:index="index"
                    v-bind:key="targetEl"
                    class="rule-column-selector-target">
                    {{ colHeaders[targetEl] }}
                    <span class="fa fa-times rule-column-selector-target-remove" @click="handleRemove(index)"></span>
                    <span class="fa fa-arrow-up rule-column-selector-up" v-if="index !== 0" @click="moveUp(index)"></span>
                    <span class="fa fa-arrow-down rule-column-selector-down" v-if="index < target.length - 1" @click="moveUp(index + 1)"></span>
                </li>
                <li v-if="this.target.length < this.colHeaders.length">
                    <span class="rule-column-selector-target-add" v-if="!orderedEdit">
                        <i @click="$emit('update:orderedEdit', true)">... {{ l("Assign Another Column") }}</i>
                    </span>
                    <span class="rule-column-selector-target-select" v-else>
                        <select2 @input="handleAdd" placeholder="Select a column">
                            <option /><!-- empty option selection for placeholder -->
                            <option v-for="(col, index) in remainingHeaders" :value="index">{{ col }}</option>
                        </select2>
                    </span>
                </li>
            </ol>
        </div>
    `,
    data: function() {
        return {
            l: _l,
        }
    },
    props: {
        target: {
            required: true
        },
        label: {
            required: false,
            type: String,
            default: _l("From Column"),
        },
        colHeaders: {
            type: Array,
            required: true
        },
        multiple: {
            type: Boolean,
            required: false,
            default: false,
        },
        ordered: {
            type: Boolean,
            required: false,
            default: false,
        },
        valueAsList: {
            type: Boolean,
            required: false,
            default: false,
        },
        orderedEdit: {
            type: Boolean,
            required: false,
            default: false,
        }
    },
    computed: {
        remainingHeaders() {
            const colHeaders = this.colHeaders;
            if(!this.multiple) {
                return colHeaders;
            }
            const remaining = {};
            for(let key in colHeaders) {
                if(this.target.indexOf(parseInt(key)) === -1) {
                    remaining[key] = colHeaders[key];
                }
            }
            return remaining;
        }
    },
    methods: {
        handleInput(value) {
            if(this.multiple) {
                // https://stackoverflow.com/questions/262427/why-does-parseint-yield-nan-with-arraymap
                let val = value.map((idx) => parseInt(idx));
                this.$emit('update:target', val);
            } else {
                let val = parseInt(value);
                if(this.valueAsList) {
                    val = [val];
                }
                this.$emit('update:target', val);
            }
        },
        handleAdd(value) {
            this.target.push(parseInt(value));
            this.$emit('update:orderedEdit', false);
        },
        handleRemove(index) {
            this.target.splice(index, 1);
        },
        moveUp(value) {
            const swapVal = this.target[value - 1];
            Vue.set(this.target, value - 1, this.target[value]);
            Vue.set(this.target, value, swapVal);
        }
    },
    components: {
        Select2,
    }
}


const RegularExpressionInput = {
    template: `
        <div><label>
            Regular Expression
            <input class="rule-regular-expression" type="text" :value="target" @input="$emit('update:target', $event.target.value)" />
        </label></div>
    `,
    props: {
        target: {
             required: true
        },
    }
}


const RuleDisplay = {
    template: `
        <li class="rule">
            <span class="rule-display">{{ title }}
                <span class="fa fa-edit" @click="edit"></span>
                <span class="fa fa-times" @click="remove"></span>
            </span>
            <span class="rule-warning" v-if="rule.warn">
                {{ rule.warn }}
            </span>
            <span class="rule-error" v-if="rule.error">
                <span class="alert-message">{{ rule.error }}</span>
            </span>
        </li>
    `,
    props: {
        rule: {
           required: true,
           type: Object,
        },
        colHeaders: {
            type: Array,
            required: true
        },
    },
    computed: { 
        title() {
            const ruleType = this.rule.type;
            return Rules[ruleType].display(this.rule, this.colHeaders);
        }
    },
    methods: {
        edit() {
            this.$emit('edit');
        },
        remove() {
            this.$emit('remove');
        }
    },
}

const IdentifierDisplay = {
    template: `
      <li class="rule" :title="help">
        Set {{ columnsLabel }} as {{ typeDisplay }}
        <span class="fa fa-edit" @click="edit"></span>
        <span class="fa fa-times" @click="remove"></span>
      </li>
    `,
    props: {
        type: {
            type: String,
            required: true
        },
        columns: {
            required: true
        },
        colHeaders: {
            type: Array,
            required: true
        },
    },
    methods: {
        remove() {
            this.$emit('remove');
        },
        edit() {
            this.$emit('edit');
        }
    },
    computed: {
        typeDisplay() {
            return MAPPING_TARGETS[this.type].label;
        },
        help() {
            return MAPPING_TARGETS[this.type].help || '';
        },
        columnsLabel() {
            let columnNames;
            if(typeof this.columns == "object") {
                columnNames = this.columns.map(idx => this.colHeaders[idx]);
            } else {
                columnNames = [this.colHeaders[this.columns]];
            }
            if(columnNames.length == 2) {
                return "columns " + columnNames[0] + " and " + columnNames[1];
            } else if(columnNames.length > 2) {
                return "columns " + columnNames.slice(0, -1).join(", ") + ", and " + columnNames[columnNames.length - 1];
            } else {
                return "column " + columnNames[0];
            }
        }
    }
}


const RuleTargetComponent = {
    template: `<li><a class="rule-link" :class="linkClassName" @click="builder.addNewRule(ruleType)">{{title}}</a></li>`,
    props: {
        ruleType: {
            type: String,
            required: true,
        },
        builder: {
            required: true,
        }
    },
    computed: {
        linkClassName() {
            return 'rule-link-' + this.ruleType.replace(/_/g, "-");
        },
        title() {
            return Rules[this.ruleType].title;
        }
    }
}


const RuleComponent = {
    template: `
    <div v-if="ruleType == displayRuleType" class="rule-editor" :class="typeToClass">
        <slot></slot>
        <div class="buttons" style="margin: 5px; height: 25px;">
           <button type="button" class="ui-button-default btn btn-default rule-editor-ok" @click="okay">Okay</button>
           <button type="button" class="ui-button-default btn rule-editor-cancel" @click="cancel">Cancel</button>
        </div>
    </div>`,
    props: {
        ruleType: {
            type: String,
            required: true,
        },
        displayRuleType: {
            required: true,
        },
        builder: {
            required: true,
        },
    },
    methods: {
        cancel() {
            this.builder.displayRuleType = null;
        },
        okay() {
            this.builder.handleRuleSave(this.ruleType);
            this.cancel();
        },
    },
    computed: {
        typeToClass() {
            return 'rule-edit-' + this.ruleType.replace(/_/g, "-");
        },
    }
}

const StateDiv = {
    template: `<div class="rule-collection-creator collection-creator flex-row-container"><slot></slot></div>`
}

const OptionButtonsDiv = {
    template: `<div class="actions clear vertically-spaced"><div class="main-options pull-right"><slot></slot></div></div>`
}

const flatMap = (f,xs) => {
    return xs.reduce((acc,x) => acc.concat(f(x)), []);
}

export default {
  data: function() {
    let mapping;
    if(this.elementsType == "ftp") {
      mapping = [{"type": "ftp_path", "columns": [0]}];
    } else if(this.elementsType == "datasets") {
      mapping = [{"type": "list_identifiers", "columns": [1]}];
    } else {
      // TODO: incorrect to ease testing, fix.    
      // mapping = [{"type": "url", "columns": [0]}, {"type": "list_identifiers", "columns": [1]}, {"type": "paired_identifier", "columns": [3]}, {"type": "collection_name", "columns": [5]}];
      mapping = [];
    }
    return {
        rules: [],
        colHeadersPerRule: [],
        mapping: mapping,
        state: 'build',  // 'build', 'error', 'wait',
        ruleView: 'normal', // 'normal' or 'source'
        ruleSource: '',
        ruleSourceError: null,
        errorMessage: '',
        hasRuleErrors: false,
        jaggedData: false,
        waitingJobState: 'new',
        titleReset: _l("Undo all reordering and discards"),
        titleNumericSort: _l("By default columns will be sorted lexiographically, check this option if the columns are numeric values and should be sorted as numbers."),
        titleInvertFilterRegex: _l("Remove rows not matching the specified regular expression at specified column."),
        titleInvertFilterEmpty: _l("Remove rows that have non-empty values at specified column."),
        titleInvertFilterMatches: _l("Remove rows not matching supplied value."),
        titleViewSource: _l("Advanced Option: View and or edit the JSON representation of the rules to apply to this tabular data."),
        namePlaceholder: _l("Enter a name for your new collection"),
        activeRuleIndex: null,
        addColumnRegexTarget: 0,
        addColumnBasenameTarget: 0,
        addColumnRegexExpression: "",
        addColumnRegexReplacement: null,
        addColumnRegexGroupCount: null,
        addColumnRegexType: "global",
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
        orientation: "vertical",
    };
  },
  props: {
    initialElements: {
        type: Array,
        required: true
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
    }
  },
  computed: {
    hasActiveMappingEdit() {
        const has = _.any(_.values(this.mapping), (mapping) => mapping.editing);
        return has;
    },
    activeRule() {
        return this.activeRuleIndex !== null && this.rules[this.activeRuleIndex];
    },
    activeRuleColHeaders() {
        const rulesHeaders = (this.activeRuleIndex !== null && this.colHeadersPerRule[this.activeRuleIndex]);
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
      for(let mapping of this.mapping) {
        targets.push(mapping.type);
      }
      return targets;
    },
    unmappedTargets() {
      const targets = [];
      const mappedTargets = this.mappedTargets;
      for(let target in MAPPING_TARGETS) {
        const targetModes = MAPPING_TARGETS[target].modes;

        if(targetModes && targetModes.indexOf(this.elementsType) < 0) {
          continue;
        }

        const targetDefinition = MAPPING_TARGETS[target];
        const targetImportType = targetDefinition.importType;
        if(targetImportType && this.importType != targetImportType) {
            continue;
        }
        if (!this.ftpUploadSite && targetDefinition.requiresFtp) {
            continue;
        }
        if(mappedTargets.indexOf(target) < 0) {
          targets.push(target);
        }
      }
      return targets;
    },
    hotData() {
      let data, sources;
      if(this.elementsType == "datasets") {
        data = this.initialElements.map(el => [el["hid"], el["name"]]);
        sources = this.initialElements.slice();
      } else {
        data = this.initialElements.slice();
        sources = data.map(el => null);
      }

      let hasRuleError = false;
      this.colHeadersPerRule = [];
      for(var ruleIndex in this.rules) {
        const ruleHeaders = this.colHeadersFor(data);
        this.colHeadersPerRule[ruleIndex] = ruleHeaders;

        const rule = this.rules[ruleIndex];
        rule.error = null;
        rule.warn = null;
        if(hasRuleError) {
          rule.warn = _l("Skipped due to previous errors.");
          continue;
        }
        var ruleType = rule.type;
        const ruleDef = Rules[ruleType];
        const res = ruleDef.apply(rule, data, sources);
        if (res.error) {
          hasRuleError = true;
          rule.error = res.error;
        } else {
          if (res.warn) {
            rule.warn = res.warn;
          }
          data = res.data || data;
          sources = res.sources || sources;
        }
      }
      return {data, sources};
    },
    colHeaders() {
      const data = this.hotData["data"];
      return this.colHeadersFor(data);
    },
    colHeadersDisplay() {
        const formattedHeaders = [];
        for (let colIndex in this.colHeaders) {
            const colHeader = this.colHeaders[colIndex];
            formattedHeaders[colIndex] =  `<b>${_.escape(colHeader)}</b>`;
            const mappingDisplay = [];
            for (let mapping of this.mapping) {
                if (mapping.columns.indexOf(parseInt(colIndex)) !== -1) {
                    const mappingDef = MAPPING_TARGETS[mapping.type];
                    mappingDisplay.push(`<i>${_.escape(mappingDef.columnHeader || mappingDef.label)}</i>`)
                }
            }
            if (mappingDisplay.length == 1) {
                formattedHeaders[colIndex] += ` (${mappingDisplay[0]})`
            } else if (mappingDisplay.length > 1) {
                formattedHeaders[colIndex] += ` (${[mappingDisplay.slice(0, -1).join(', '), mappingDisplay.slice(-1)[0]].join(' & ')})`;
            }
        }
        return formattedHeaders;
    },
    mappingAsDict() {
      const asDict = {};
      for(let mapping of this.mapping) {
        asDict[mapping.type] = mapping;
      }
      return asDict;
    },
    collectionType() {
      let identifierColumns = []
      if(this.mappingAsDict.list_identifiers) {
          identifierColumns = this.mappingAsDict.list_identifiers.columns;
      }
      let collectionType = identifierColumns.map(col => "list").join(":");
      if(this.mappingAsDict.paired_identifier) {
          collectionType += ":paired";
      }
      return collectionType;
    },
    validInput() {
        const identifierColumns = this.identifierColumns();
        const mappingAsDict = this.mappingAsDict;
        const buildingCollection = identifierColumns.length > 0;

        let valid = true;
        if(buildingCollection && !mappingAsDict.collection_name) {
            valid = this.collectionName.length > 0;
        }

        if(mappingAsDict.ftp_path && mappingAsDict.url) {
            // Can only specify one of these.
            valid = false;
        }

        for(var rule of this.rules) {
          if(rule.error) {
            valid = false;
          }
        }

        // raw tabular variant can build stand-alone datasets without identifier
        // columns for the collection builder for existing datasets cannot do this.
        if(this.elementsType == "datasets" && identifierColumns.length == 0) {
            valid = false;
        }
        return valid;
    }
  },
  methods: {
    l(str) {  // _l conflicts private methods of Vue internals, expose as l instead
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
      this.resetRules()
      this.state = 'build';
      this.errorMessage = '';
      this.collectionName = '';
    },
    addNewRule(ruleType) {
      Rules[ruleType].init(this);
      this.displayRuleType = ruleType;
      this.activeRuleIndex = null;
    },
    handleRuleSave(ruleType) {
      const rule = this.activeRule;
      if(rule) {
        Rules[ruleType].save(this, rule);
      } else {
        const rule = {"type": ruleType};
        Rules[ruleType].save(this, rule);
        this.rules.push(rule);
      }
    },
    viewSource() {
        this.resetSource();
        this.ruleView = 'source';
    },
    resetSource() {
        const replacer = function(key, value) {
            if(key == "error" || key == "warn") {
                return undefined;
            }
            return value;
        }
        const asJson = {
            "rules": this.rules,
            "mapping": this.mapping,
        }
        if (this.extension !== UploadUtils.DEFAULT_EXTENSION) {
            asJson.extension = this.extension;
        }
        if (this.genome !== UploadUtils.DEFAULT_GENOME) {
            asJson.genome = this.genome;
        }
        this.ruleSource = JSON.stringify(asJson, replacer, '  ');
        this.ruleSourceError = null;
    },
    attemptRulePreview() { // Leave source mode if rules are valid and view.
        this.ruleSourceError = null;
        let asJson;
        try {
            asJson = JSON.parse(this.ruleSource);
        } catch (error) {
            this.ruleSourceError = "Problem parsing your rules.";
            return;
        }
        this.updateFromSource(asJson);
        this.ruleView = 'normal';
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
    handleColumnMapping() {

    },
    colHeadersFor(data) {
      if(data.length == 0) {
          return [];
      } else {
          return data[0].map((el, i) => String.fromCharCode(65 + i));
      }
    },
    addIdentifier(identifier) {
      const multiple = this.mappingTargets()[identifier].multiple;
      // If multiple selection, pop open a new column selector in edit mode.
      const initialColumns = multiple ? [] : [0];
      this.mapping.push({"type": identifier, "columns": initialColumns, "editing": multiple});
    },
    editRule(rule, index) {
       const ruleType = rule.type;
       this.activeRuleIndex = index;
       Rules[ruleType].init(this, rule);
       this.displayRuleType = ruleType;
    },
    removeRule(index) {
        this.rules.splice(index, 1);
    },
    removeMapping(index) {
        this.mapping.splice(index, 1);
    },
    refreshAndWait(response) {
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
                this.state = 'error';
                this.errorMessage = "Unknown error encountered while running your upload job, this could be a server issue or a problem with the upload definition.";
            } else {
                const history = parent.Galaxy && parent.Galaxy.currHistoryPanel && parent.Galaxy.currHistoryPanel.model;
                history.refresh();
                this.oncreate();
            }
        }
        const doJobCheck = () => {
            axios
                .get(`${Galaxy.root}api/jobs/${jobId}`)
                .then(handleJobShow)
                .catch(this.renderFetchError);
        }
        setTimeout(doJobCheck, 1000);
    },
    renderFetchError(error) {
        this.state = 'error';
        if(error.response) {
            console.log(error.response);
            this.errorMessage = error.response.data.err_msg;        
        } else {
            console.log(error);
            this.errorMessage = "Unknown error encountered: " + error;
        }
    },
    swapOrientation() {
        this.orientation = this.orientation == 'horizontal' ? 'vertical' : 'horizontal';
        const hotTable = this.$refs.hotTable.table;
        if(this.orientation == "horizontal") {
            this.$nextTick(function() {
                const fullWidth = $(".rule-builder-body").width();
                hotTable.updateSettings({
                    width: fullWidth,
                });
            });
        } else {
            this.$nextTick(function() {
                const fullWidth = $(".rule-builder-body").width();
                hotTable.updateSettings({
                    width: fullWidth - 270,
                });
            });
        }
    },
    createCollection() {
        this.state = 'wait';
        const name = this.collectionName;
        const collectionType = this.collectionType;
        if(this.elementsType == "datasets") {
            const elements = this.creationElementsFromDatasets();
            const response = this.creationFn(
                elements, collectionType, name
            )
            response.done(this.oncreate);
            response.error(this.renderFetchError);
        } else {
            const historyId = Galaxy.currHistoryPanel.model.id;
            let elements, targets;
            if(collectionType) {
                targets = [];
                const elementsByCollectionName = this.creationElementsForFetch();
                for(let collectionName in elementsByCollectionName) {
                    const target = {
                        "destination": {"type": "hdca"},
                        "elements": elementsByCollectionName[collectionName],
                        "collection_type": collectionType,
                        "name": collectionName,
                    };
                    targets.push(target);
                }
            } else {
                elements = this.creationDatasetsForFetch();                
                targets = [{
                    "destination": {"type": "hdas"},
                    "elements": elements,
                    "name": name,
                }];
            }

            axios
                .post(`${Galaxy.root}api/tools/fetch`, {
                    "history_id": historyId,
                    "targets": targets,
                })
                .then(this.refreshAndWait)
                .catch(this.renderFetchError);
        }
    },
    identifierColumns() {
        const mappingAsDict = this.mappingAsDict;
        let identifierColumns = []
        if(mappingAsDict.list_identifiers) {
            identifierColumns = mappingAsDict.list_identifiers.columns.slice();        
        }
        if(this.mappingAsDict.paired_identifier) {
            identifierColumns.push(this.mappingAsDict.paired_identifier.columns[0]);
        }
        return identifierColumns;
    },
    buildRequestElements(createDatasetDescription, createSubcollectionDescription, subElementProp) {
        const data = this.hotData["data"];
        const identifierColumns = this.identifierColumns();
        if(identifierColumns.length < 1) {
          console.log("Error but this shouldn't have happened, create button should have been disabled.");
          return;
        }

        const numIdentifierColumns = identifierColumns.length;
        const collectionType = this.collectionType;
        const elementsByName = {};

        let dataByCollection = {};
        const collectionNameMap = this.mappingAsDict.collection_name;
        if(collectionNameMap) {
            const collectionNameTarget = collectionNameMap.columns[0];
            for(let dataIndex in data) {
                const row = data[dataIndex];
                const name = row[collectionNameTarget];
                if(!dataByCollection[name]) {
                    dataByCollection[name] = {};
                }
                dataByCollection[name][dataIndex] = row;
            }
        } else {
            // use global collection name from the form.
            dataByCollection[this.collectionName] = data;
        }

        for(let collectionName in dataByCollection) {
            const elements = [];

            for(let dataIndex in dataByCollection[collectionName]) {
                const rowData = data[dataIndex];

                // For each row, find place in depth for this element.
                let collectionTypeAtDepth = collectionType;
                let elementsAtDepth = elements;

                for(let identifierColumnIndex = 0; identifierColumnIndex < numIdentifierColumns; identifierColumnIndex++) {
                    let identifier = rowData[identifierColumns[identifierColumnIndex]];
                    if(identifierColumnIndex + 1 == numIdentifierColumns) {
                        // At correct final position in nested structure for this dataset.
                        if(collectionTypeAtDepth === "paired") {
                            if(["f", "1", "r1", "forward"].indexOf(identifier.toLowerCase()) > -1) {
                                identifier = "forward";
                            } 
                            else if(["r", "2", "r2", "reverse"].indexOf(identifier.toLowerCase()) > -1) {
                                identifier = "reverse";
                            }
                            else {
                                this.state = 'error';
                                this.errorMessage = 'Unknown indicator of paired status encountered - only values of F, R, 1, 2, R1, R2, forward, or reverse are allowed.';
                            }
                        }
                        const element = createDatasetDescription(dataIndex, identifier);
                        elementsAtDepth.push(element);
                    } else {
                        // Create nesting for this element.
                        collectionTypeAtDepth = collectionTypeAtDepth.split(":").slice(1).join(":");
                        let found = false;
                        for(let element of elementsAtDepth) {
                            if(element["name"] == identifier) {
                                elementsAtDepth = element[subElementProp];
                                found = true;
                                break;
                            }
                        }
                        if(!found) {
                            const subcollection = createSubcollectionDescription(identifier);
                            elementsAtDepth.push(subcollection);
                            const childCollectionElements = [];
                            subcollection[subElementProp] = childCollectionElements;
                            subcollection.collection_type = collectionTypeAtDepth;
                            elementsAtDepth = childCollectionElements;
                        }
                    }
                }
            }

            elementsByName[collectionName] = elements;
        }


        return elementsByName;
    },
    creationElementsFromDatasets() {
        const sources = this.hotData["sources"];
        const data = this.hotData["data"];

        const elementsByCollectionName = this.buildRequestElements(
            (dataIndex, identifier) => {
                const source = sources[dataIndex];
                return {"id": source["id"], "name": identifier, "src": "hda"}
            },
            (identifier) => {
                return {"name": identifier, "src": "new_collection"};
            },
            "element_identifiers",
        );
        // This modality only allows a single collection to be created currently.
        return elementsByCollectionName[this.collectionName];
    },
    creationElementsForFetch() { // fetch elements for HDCA
        const data = this.hotData["data"];
        const mappingAsDict = this.mappingAsDict;

        const elementsByCollectionName = this.buildRequestElements(
            (dataIndex, identifier) => {
                const res = this._datasetFor(dataIndex, data, mappingAsDict);
                res["name"] = identifier;
                return res;
            },
            (identifier) => {
                return {"name": identifier};
            },
            "elements",
        );

        return elementsByCollectionName;
    },
    creationDatasetsForFetch() { // fetch elements for HDAs if not collection information specified.
        const data = this.hotData["data"];
        const mappingAsDict = this.mappingAsDict;

        const datasets = [];

        for(let dataIndex in data) {
            const rowData = data[dataIndex];
            const res = this._datasetFor(dataIndex, data, mappingAsDict);
            datasets.push(res);
        }

        return datasets;
    },
    highlightColumn(n) {
        const headerSelection = $(`.htCore > thead > tr > th:nth-child(${n + 1})`);
        headerSelection.addClass('ht__highlight');
        const bodySelection = $(`.htCore > tbody > tr > td:nth-child(${n + 1})`);
        bodySelection.addClass('rule-highlight');
    },
    unhighlightColumn(n) {
        const headerSelection = $(`.htCore > thead > tr > th:nth-child(${n + 1})`);
        headerSelection.removeClass('ht__highlight');
        const bodySelection = $(`.htCore > tbody > tr > td:nth-child(${n + 1})`);
        bodySelection.removeClass('rule-highlight');
    },
    _datasetFor(dataIndex, data, mappingAsDict) {
        const res = {};
        if(mappingAsDict.url) {
            const urlColumn = mappingAsDict.url.columns[0];
            let url = data[dataIndex][urlColumn];
            if(url.indexOf("://") == -1) {
                url = "http://" + url;
            }
            res["url"] = url;
            res["src"] = "url";
        } else {
            const ftpPathColumn = mappingAsDict.ftp_path.columns[0];
            const ftpPath = data[dataIndex][ftpPathColumn];
            res["ftp_path"] = ftpPath;
            res["src"] = "ftp_path";
        }
        if(mappingAsDict.dbkey) {
            const dbkeyColumn = mappingAsDict.dbkey.columns[0];
            const dbkey = data[dataIndex][dbkeyColumn];
            res["dbkey"] = dbkey;
        } else if(this.genome) {
            res["dbkey"] = this.genome;
        }
        if(mappingAsDict.file_type) {
            const fileTypeColumn = mappingAsDict.file_type.columns[0];
            const fileType = data[dataIndex][fileTypeColumn];
            res["ext"] = file_type;
        } else if(this.extension) {
            res["ext"] = this.extension;
        }
        if(mappingAsDict.name) {
            const nameColumn = mappingAsDict.name.columns[0];
            const name = data[dataIndex][nameColumn];
            res["name"] = name;
        }
        if(mappingAsDict.info) {
            const infoColumn = mappingAsDict.info.columns[0];
            const info = data[dataIndex][infoColumn];
            res["info"] = info;
        }
        return res;
    },
  },
  created() {
      let columnCount = null;
      if(this.elementsType == "datasets") {
          for(let element of this.initialElements) {
              if(element.history_content_type == "dataset_collection") {
                  this.errorMessage = "This component can only be used with datasets, you have specified one or more collections.";
                  this.state = 'error';
              }
          }
      } else {
          for(let row of this.initialElements) {
              if (columnCount == null) {
                  columnCount = row.length;
              } else {
                  if(columnCount != row.length) {
                      this.jaggedData = true;
                      break
                  }
              }
          }
      }
      UploadUtils.getUploadDatatypes((extensions) => {this.extensions = extensions; this.extension = UploadUtils.DEFAULT_EXTENSION}, false, UploadUtils.AUTO_EXTENSION);
      UploadUtils.getUploadGenomes((genomes) => {this.genomes = genomes; this.genome = UploadUtils.DEFAULT_GENOME;}, UploadUtils.DEFAULT_GENOME);
  },
  watch: {
      'addColumnRegexType': function (val) {
          if (val == "groups") {
              this.addColumnRegexGroupCount = 1;
          }
          if (val == "replacement") {
              this.addColumnRegexReplacement = "$&";
          }
      },
  },
  components: {
    HotTable,
    RuleComponent,
    RuleTargetComponent,
    RuleDisplay,
    IdentifierDisplay,
    ColumnSelector,
    RegularExpressionInput,
    StateDiv,
    OptionButtonsDiv,
    Select2,
  }
}
</script>

<style>
  .table-column {
    width: 100%;
    /* overflow: scroll; */
  }
  .vertical #hot-table {
    width: 100%;
    overflow: scroll;
    height: 400px;
  }
  .horizontal #hot-table {
    width: 100%;
    overflow: scroll;
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
  .rules-container {
    border: 1px dashed #ccc;
    padding: 5px;
  }
  .rules-container-vertical {
    width: 270px;
    height: 400px;
  }
  .rules-container-horizontal {
    width: 100%;
    height: 150px;
  }
  .rules-container .title {
    font-weight: bold;
  }
  .rule-option {
    padding-left: 20px;
  }
  .rule-summary {
    height: 100%;
    display: flex;
    flex-direction: column;
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
  /* .dropdown-menu {position:absolute;} */
</style>
