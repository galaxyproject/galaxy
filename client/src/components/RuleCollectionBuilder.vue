<template>
    <StateDiv v-if="state == 'build'" class="rule-collection-builder">
        <!-- 如果是从单独的数据集构建与初始化数据导入时的不同说明-->
        <RuleModalHeader v-if="ruleView == 'source'">
            以下是应用于表格数据的原始JSON规则描述。这是一个高级设置。
        </RuleModalHeader>
        <RuleModalHeader v-else-if="elementsType == 'datasets' || elementsType == 'library_datasets'">
            使用此表单描述如何从指定数据集中构建集合。<b>确保至少指定一列作为列表标识符</b> —— 指定更多列以创建嵌套列表结构。指定一列作为“集合名称”以将数据集分组到多个集合中。
        </RuleModalHeader>
        <!-- 该模态允许导入单个数据集、多个集合，并且需要数据源 - 请注意。-->
        <RuleModalHeader v-else-if="importType == 'datasets'">
            使用此表单描述导入数据集的规则。至少需要定义一列作为数据源来获取数据（URL、FTP文件等）。
        </RuleModalHeader>
        <RuleModalHeader v-else>
            使用此表单描述导入数据集的规则。至少需要定义一列作为数据源来获取数据（URL、FTP文件等）。
            <b>确保至少指定一列作为列表标识符</b> —— 指定更多列以创建嵌套列表结构。指定一列作为“集合名称”以将数据集分组到多个集合中。
        </RuleModalHeader>
        <b-alert v-if="validityErrorMessages.length != 0" class="alert-area" show variant="warning" dismissible>
            {{ validityErrorHeader }}
            <ul>
                <li v-for="error in validityErrorMessages" :key="error">
                    {{ error }}
                </li>
            </ul>
        </b-alert>
        <RuleModalMiddle v-if="ruleView == 'source'">
            <p v-if="ruleSourceError" class="errormessagelarge">{{ ruleSourceError }}</p>
            <textarea v-model="ruleSource" class="rule-source"></textarea>
        </RuleModalMiddle>

        <RuleModalMiddle v-else>
            <!-- 列头 -->
            <div
                v-if="ruleView == 'normal'"
                class="rule-builder-body vertically-spaced"
                :class="{ 'flex-column-container': vertical }">
                <!-- width: 30%; -->
                <div class="rule-column" :class="orientation">
                    <div
                        class="rules-container"
                        :class="{
                            'rules-container-vertical': initialElements && vertical,
                            'rules-container-horizontal': initialElements && horizontal,
                            'rules-container-full': initialElements == null,
                        }">
                        <RuleComponent
                            rule-type="sort"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addSortingTarget" :col-headers="activeRuleColHeaders" />
                            <label v-b-tooltip.hover :title="titleNumericSort">
                                <input v-model="addSortingNumeric" type="checkbox" />
                                {{ l("数字排序") }}
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_basename"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector
                                :target.sync="addColumnBasenameTarget"
                                :col-headers="activeRuleColHeaders" />
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_rownum"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <label>
                                {{ l("从") }}
                                <input v-model="addColumnRownumStart" type="number" min="0" />
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_metadata"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <label>
                                {{ l("为") }}
                                <select v-model="addColumnMetadataValue">
                                    <option v-for="(col, index) in metadataOptions" :value="index">{{ col }}</option>
                                </select>
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_group_tag_value"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <label>
                                {{ l("值") }}
                                <input v-model="addColumnGroupTagValueValue" type="text" />
                            </label>
                            <label>
                                {{ l("默认值") }}
                                <input v-model="addColumnGroupTagValueDefault" type="text" />
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_regex"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addColumnRegexTarget" :col-headers="activeRuleColHeaders" />
                            <label>
                                <input v-model="addColumnRegexType" type="radio" value="global" />创建匹配表达式的列。
                            </label>
                            <br />
                            <label>
                                <input v-model="addColumnRegexType" type="radio" value="groups" />创建匹配表达式组的列。
                            </label>
                            <br />
                            <label>
                                <input v-model="addColumnRegexType" type="radio" value="replacement" />创建基于表达式替换的列。
                            </label>
                            <br />
                            <RegularExpressionInput :target.sync="addColumnRegexExpression" />
                            <label v-if="addColumnRegexType == 'groups'">
                                {{ l("组数") }}
                                <input v-model="addColumnRegexGroupCount" type="number" min="1" />
                            </label>
                            <label v-if="addColumnRegexType == 'replacement'">
                                {{ l("替换表达式") }}
                                <input v-model="addColumnRegexReplacement" type="text" class="rule-replacement" />
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_concatenate"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector
                                :target.sync="addColumnConcatenateTarget0"
                                :col-headers="activeRuleColHeaders" />
                            <ColumnSelector
                                :target.sync="addColumnConcatenateTarget1"
                                :col-headers="activeRuleColHeaders" />
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_substr"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addColumnSubstrTarget" :col-headers="activeRuleColHeaders" />
                            <label>
                                <select v-model="addColumnSubstrType">
                                    <option value="keep_prefix">仅保留指定的前缀。</option>
                                    <option value="drop_prefix">去掉指定的前缀。</option>
                                    <option value="keep_suffix">仅保留指定的后缀。</option>
                                    <option value="drop_suffix">去掉指定的后缀。</option>
                                </select>
                            </label>
                            <label>
                                {{ l("前缀或后缀长度") }}
                                <input v-model="addColumnSubstrLength" type="number" min="0" />
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_column_value"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <label>
                                {{ l("值") }}
                                <input v-model="addColumnValue" type="text" />
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="remove_columns"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector
                                :target.sync="removeColumnTargets"
                                :col-headers="activeRuleColHeaders"
                                :multiple="true" />
                        </RuleComponent>
                        <RuleComponent
                            rule-type="split_columns"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector
                                :target.sync="splitColumnsTargets0"
                                label="奇数行列"
                                :col-headers="activeRuleColHeaders"
                                :multiple="true" />
                            <ColumnSelector
                                :target.sync="splitColumnsTargets1"
                                label="偶数行列"
                                :col-headers="activeRuleColHeaders"
                                :multiple="true" />
                        </RuleComponent>
                        <RuleComponent
                            rule-type="swap_columns"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector
                                :target.sync="swapColumnsTarget0"
                                label="交换列"
                                :col-headers="activeRuleColHeaders" />
                            <ColumnSelector
                                :target.sync="swapColumnsTarget1"
                                label="与列"
                                :col-headers="activeRuleColHeaders" />
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_filter_regex"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addFilterRegexTarget" :col-headers="activeRuleColHeaders" />
                            <RegularExpressionInput :target.sync="addFilterRegexExpression" />
                            <label v-b-tooltip.hover :title="titleInvertFilterRegex">
                                <input v-model="addFilterRegexInvert" type="checkbox" />
                                {{ l("反转过滤") }}
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_filter_matches"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addFilterMatchesTarget" :col-headers="activeRuleColHeaders" />
                            <input v-model="addFilterMatchesValue" type="text" />
                            <label v-b-tooltip.hover :title="titleInvertFilterMatches">
                                <input v-model="addFilterMatchesInvert" type="checkbox" />
                                {{ l("反转过滤") }}
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_filter_compare"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addFilterCompareTarget" :col-headers="activeRuleColHeaders" />
                            <label>
                                过滤出行
                                <select v-model="addFilterCompareType">
                                    <option value="less_than">{{ l("小于") }}</option>
                                    <option value="less_than_equal">{{ l("小于或等于") }}</option>
                                    <option value="greater_than">{{ l("大于") }}</option>
                                    <option value="greater_than_equal">{{ l("大于或等于") }}</option>
                                </select>
                            </label>
                            <input v-model="addFilterCompareValue" type="text" />
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_filter_count"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <label>
                                过滤哪一行？
                                <select v-model="addFilterCountWhich">
                                    <option value="first">第一行</option>
                                    <option value="last">最后一行</option>
                                </select>
                            </label>
                            <label>
                                过滤多少行？
                                <input v-model="addFilterCountN" type="number" />
                            </label>
                            <label v-b-tooltip.hover :title="titleInvertFilterMatches">
                                <input v-model="addFilterCountInvert" type="checkbox" />
                                {{ l("反转过滤") }}
                            </label>
                        </RuleComponent>
                        <RuleComponent
                            rule-type="add_filter_empty"
                            :display-rule-type.sync="displayRuleType"
                            @saveRule="handleRuleSave">
                            <ColumnSelector :target.sync="addFilterEmptyTarget" :col-headers="activeRuleColHeaders" />
                            <label v-b-tooltip.hover :title="titleInvertFilterEmpty">
                                <input v-model="addFilterEmptyInvert" type="checkbox" />
                                {{ l("反转过滤") }}
                            </label>
                        </RuleComponent>
                        <div v-if="displayRuleType == 'mapping'">
                            <div v-for="(map, index) in mapping" :key="map.type" class="map" :index="index">
                                <ColumnSelector
                                    :class="'rule-map-' + map.type.replace(/_/g, '-')"
                                    :label="mappingTargets()[map.type].label"
                                    :help="mappingTargets()[map.type].help"
                                    :target.sync="map.columns"
                                    :ordered-edit.sync="map.editing"
                                    :col-headers="colHeaders"
                                    :multiple="mappingTargets()[map.type].multiple"
                                    :ordered="true"
                                    :value-as-list="true">
                                    <span
                                        v-b-tooltip.hover
                                        :title="titleRemoveMapping"
                                        class="fa fa-times"
                                        @click="removeMapping(index)"></span>
                                </ColumnSelector>
                            </div>
                            <div class="buttons rule-edit-buttons d-flex justify-content-end">
                                <button
                                    v-if="unmappedTargets.length > 0"
                                    type="button"
                                    class="dropdown-toggle btn btn-primary mr-1"
                                    data-toggle="dropdown">
                                    <span class="fa fa-plus rule-add-mapping"></span>
                                    {{ "添加定义" }}
                                    <span class="caret"></span>
                                </button>
                                <div class="dropdown-menu" role="menu">
                                    <a
                                        v-for="target in unmappedTargets"
                                        :key="target"
                                        :index="target"
                                        class="dropdown-item"
                                        href="javascript:void(0)"
                                        :class="'rule-add-mapping-' + target.replace(/_/g, '-')"
                                        @click="addIdentifier(target)"
                                        >{{ mappingTargets()[target].label }}</a
                                    >
                                </div>
                                <b-button
                                    v-if="!hasActiveMappingEdit"
                                    v-b-tooltip.hover.bottom
                                    :title="titleApplyColumnDefinitions"
                                    class="rule-mapping-ok"
                                    @click="displayRuleType = null"
                                    >{{ l("应用") }}</b-button
                                >
                            </div>
                        </div>
                        <div v-if="displayRuleType == null" class="rule-summary">
                            <span class="title">
                                {{ l("规则") }}
                                <span
                                    v-b-tooltip.hover
                                    class="fa fa-wrench rule-builder-view-source"
                                    :title="titleViewSource"
                                    @click="viewSource"></span>
                                <SavedRulesSelector
                                    ref="savedRulesSelector"
                                    :saved-rules="savedRules"
                                    @update-rules="restoreRules" />
                            </span>
                            <div v-if="jaggedData" class="rule-warning">
                                行包含不同数量的列，可能在解析数据时遇到问题。
                            </div>
                            <ol class="rules">
                                <RuleDisplay
                                    v-for="(rule, index) in rules"
                                    :key="index"
                                    :rule="rule"
                                    :index="index"
                                    :col-headers="colHeadersPerRule[index]"
                                    @edit="editRule(rule, index)"
                                    @remove="removeRule(index)" />
                                <IdentifierDisplay
                                    v-for="(map, index) in mapping"
                                    v-bind="map"
                                    :key="map.type"
                                    :index="index"
                                    :col-headers="colHeaders"
                                    @remove="removeMapping(index)"
                                    @edit="displayRuleType = 'mapping'"
                                    @mouseover.native="map.columns.forEach((col) => highlightColumn(col))"
                                    @mouseout.native="map.columns.forEach((col) => unhighlightColumn(col))" />
                                <div v-if="mapping.length == 0">
                                    必须指定一个或多个列定义。这些是指定如何从表格的行和列构建集合和数据集的必需项。
                                    <a href="javascript:void(0)" @click="displayRuleType = 'mapping'">点击这里</a>以管理列定义。
                                </div>
                            </ol>
                            <div class="rules-buttons btn-group">
                                <div class="dropup">
                                    <button
                                        v-b-tooltip.hover.bottom
                                        type="button"
                                        :title="titleRulesMenu"
                                        class="rule-menu-rules-button primary-button dropdown-toggle"
                                        data-toggle="dropdown">
                                        <span class="fa fa-plus"></span>
                                        {{ l("规则") }}
                                        <span class="caret"></span>
                                    </button>
                                    <div class="dropdown-menu" role="menu">
                                        <RuleTargetComponent rule-type="sort" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="remove_columns" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="split_columns" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="swap_columns" @addNewRule="addNewRule" />
                                        <a
                                            href="javascript:void(0)"
                                            class="dropdown-item rule-link rule-link-mapping"
                                            @click="displayRuleType = 'mapping'">添加 / 修改列定义</a>
                                    </div>
                                </div>
                                <div class="dropup">
                                    <button
                                        v-b-tooltip.hover.bottom
                                        type="button"
                                        :title="titleFilterMenu"
                                        class="rule-menu-filter-button primary-button dropdown-toggle"
                                        data-toggle="dropdown">
                                        <span class="fa fa-plus"></span>
                                        {{ l("筛选") }}
                                        <span class="caret"></span>
                                    </button>
                                    <div class="dropdown-menu" role="menu">
                                        <RuleTargetComponent rule-type="add_filter_regex" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_filter_matches" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_filter_compare" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_filter_empty" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_filter_count" @addNewRule="addNewRule" />
                                    </div>
                                </div>
                                <div class="dropup">
                                    <button
                                        v-b-tooltip.hover.bottom
                                        type="button"
                                        :title="titleColumMenu"
                                        class="rule-menu-column-button primary-button dropdown-toggle"
                                        data-toggle="dropdown">
                                        <span class="fa fa-plus"></span>
                                        {{ l("列") }}
                                        <span class="caret"></span>
                                    </button>
                                    <div class="dropdown-menu" role="menu">
                                        <RuleTargetComponent rule-type="add_column_basename" @addNewRule="addNewRule" />
                                        <RuleTargetComponent
                                            v-if="metadataOptions"
                                            rule-type="add_column_metadata"
                                            @addNewRule="addNewRule" />
                                        <RuleTargetComponent
                                            v-if="hasTagsMetadata"
                                            rule-type="add_column_group_tag_value"
                                            @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_column_regex" @addNewRule="addNewRule" />
                                        <RuleTargetComponent
                                            rule-type="add_column_concatenate"
                                            @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_column_rownum" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_column_value" @addNewRule="addNewRule" />
                                        <RuleTargetComponent rule-type="add_column_substr" @addNewRule="addNewRule" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <!--  flex-column列 -->
                <!--  style="width: 70%;" -->
                <div v-if="initialElements !== null" class="table-column" :class="orientation" style="width: 100%">
                    <HotTable
                        id="hot-table"
                        ref="hotTable"
                        :data="hotData.data"
                        :col-headers="colHeadersDisplay"
                        :read-only="true"
                        stretch-h="all"></HotTable>
                </div>
            </div>
        </RuleModalMiddle>
        <RuleModalFooter v-if="ruleView == 'source'">
            <b-button v-b-tooltip.hover :title="titleSourceCancel" class="rule-btn-cancel" @click="cancelSourceEdit">{{
                l("取消")
            }}</b-button>
            <b-button v-b-tooltip.hover :title="titleSourceReset" class="creator-reset-btn rule-btn-reset">{{
                l("重置")
            }}</b-button>
            <b-button v-b-tooltip.hover :title="titleSourceApply" class="rule-btn-okay" @click="attemptRulePreview">{{
                l("应用")
            }}</b-button>
        </RuleModalFooter>
        <RuleModalFooter v-else-if="ruleView == 'normal'">
            <template v-slot:inputs>
                <div class="rule-footer-inputs">
                    <label v-if="elementsType == 'datasets'">{{ l("隐藏原始元素") }}:</label>
                    <input v-if="elementsType == 'datasets'" v-model="hideSourceItems" type="checkbox" />
                    <div v-if="extension && showFileTypeSelector" class="rule-footer-extension-group">
                        <label>{{ l("类型") }}:</label>
                        <Select2 v-model="extension" name="extension" class="extension-select">
                            <option v-for="col in extensions" :key="col.id" :value="col['id']">
                                {{ col["text"] }}
                            </option>
                        </Select2>
                    </div>
                    <div v-if="genome && showGenomeSelector" class="rule-footer-genome-group">
                        <label>{{ l("基因组") }}:</label>
                        <Select2 v-model="genome" class="genome-select">
                            <option v-for="col in genomes" :key="col.id" :value="col['id']">{{ col["text"] }}</option>
                        </Select2>
                    </div>
                    <label v-if="showAddNameTag">{{ l("为名称添加标签") }}:</label>
                    <input v-if="showAddNameTag" v-model="addNameTag" type="checkbox" />
                    <div v-if="showCollectionNameInput" class="rule-footer-name-group">
                        <b-input
                            v-model="collectionName"
                            v-b-tooltip.hover
                            class="collection-name"
                            :placeholder="namePlaceholder"
                            :title="namePlaceholder" />
                        <label>{{ l("名称") }}:</label>
                    </div>
                </div>
            </template>
            <b-row class="mx-auto">
                <b-button
                    :help="titleCancel"
                    class="creator-cancel-btn rule-btn-cancel"
                    tabindex="-1"
                    @click="cancel"
                    >{{ l("取消") }}</b-button
                >

                <TooltipOnHover class="menu-option" :title="titleReset">
                    <b-button class="creator-reset-btn rule-btn-reset" @click="resetRulesAndState">{{
                        l("重置")
                    }}</b-button>
                </TooltipOnHover>
                <TooltipOnHover class="menu-option" :disabled="!validInput" :title="titleFinish">
                    <b-button
                        class="create-collection rule-btn-okay"
                        variant="primary"
                        :disabled="!validInput"
                        @click="createCollection"
                        >{{ finishButtonTitle }}</b-button
                    >
                </TooltipOnHover>
            </b-row>
        </RuleModalFooter>
    </StateDiv>
    <StateDiv v-else-if="state == 'wait'" class="rule-collection-builder">
        <RuleModalHeader v-if="importType == 'datasets'">
            {{
                l(
                    "数据集已提交给Galaxy进行创建，创建完成后此对话框将关闭。您可以随时关闭此对话框，但无法收到数据集创建的错误通知，数据集创建完成后，可能需要手动刷新历史记录以查看新数据集。"
                )
            }}
        </RuleModalHeader>
        <RuleModalHeader v-else-if="importType == 'collections'">
            {{
                l(
                    "Galaxy正在等待集合创建完成，此对话框将在完成时关闭。您可以随时关闭此对话框，但无法收到集合创建的错误通知，集合创建完成后，可能需要手动刷新历史记录以查看新集合。"
                )
            }}
        </RuleModalHeader>
        <RuleModalFooter>
            <b-button class="creator-cancel-btn" tabindex="-1" @click="cancel">{{ l("关闭") }}</b-button>
        </RuleModalFooter>
    </StateDiv>
    <StateDiv v-else-if="state == 'error'" class="rule-collection-builder">
        <!-- TODO: 从配对集合构建警告样式... -->
        <RuleModalHeader>遇到问题。</RuleModalHeader>
        <RuleModalMiddle>
            <p class="errormessagelarge">{{ errorMessage }}</p>
        </RuleModalMiddle>
        <RuleModalFooter>
            <b-button v-b-tooltip.hover :title="titleCancel" class="creator-cancel-btn" tabindex="-1" @click="cancel">{{
                l("关闭")
            }}</b-button>
            <b-button v-b-tooltip.hover :title="titleErrorOkay" tabindex="-1" @click="state = 'build'">{{
                l("确定")
            }}</b-button>
        </RuleModalFooter>
    </StateDiv>
</template>
<script>
import HotTable from "@handsontable/vue";
import { getGalaxyInstance } from "app";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import ColumnSelector from "components/RuleBuilder/ColumnSelector";
import IdentifierDisplay from "components/RuleBuilder/IdentifierDisplay";
import RegularExpressionInput from "components/RuleBuilder/RegularExpressionInput";
import RuleDefs from "components/RuleBuilder/rule-definitions";
import RuleComponent from "components/RuleBuilder/RuleComponent";
import RuleDisplay from "components/RuleBuilder/RuleDisplay";
import RuleModalFooter from "components/RuleBuilder/RuleModalFooter";
import RuleModalHeader from "components/RuleBuilder/RuleModalHeader";
import RuleModalMiddle from "components/RuleBuilder/RuleModalMiddle";
import RuleTargetComponent from "components/RuleBuilder/RuleTargetComponent";
import SavedRulesSelector from "components/RuleBuilder/SavedRulesSelector";
import SaveRules from "components/RuleBuilder/SaveRules";
import StateDiv from "components/RuleBuilder/StateDiv";
import Select2 from "components/Select2";
import UploadUtils from "components/Upload/utils";
import { ERROR_STATES, NON_TERMINAL_STATES } from "components/WorkflowInvocationState/util";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import _ from "underscore";
import _l from "utils/localization";
import Vue from "vue";

import { errorMessageAsString } from "@/utils/simple-error";
import { startWatchingHistory } from "@/watch/watchHistory";

import TooltipOnHover from "components/TooltipOnHover.vue";

Vue.use(BootstrapVue);

const RULES = RuleDefs.RULES;
const MAPPING_TARGETS = RuleDefs.MAPPING_TARGETS;

// convert deferred backbone nonsense into a promise
const deferredToPromise = (d) => {
    return new Promise((resolve, reject) => {
        d.done((_, result) => resolve(result));
        d.fail((err) => reject(err));
    });
};

export default {
    components: {
        TooltipOnHover,
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
    mixins: [SaveRules],
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
            titleReset: _l("撤销所有重新排序和丢弃操作"),
            titleNumericSort: _l(
                "默认情况下，列将按字典顺序排序。如果列为数字值且应按数字排序，请勾选此选项"
            ),
            titleInvertFilterRegex: _l("移除不符合指定正则表达式的行"),
            titleInvertFilterEmpty: _l("移除指定列中非空值的行"),
            titleInvertFilterMatches: _l("移除与提供的值匹配的行"),
            titleViewSource: _l(
                "高级选项：查看或编辑应用于此表格数据的规则的JSON表示"
            ),
            titleSourceCancel: _l("停止编辑规则并取消更改"),
            titleSourceReset: _l("将文本区域重置为当前的规则集"),
            titleSourceApply: _l("应用更改到规则源并返回规则预览"),
            titleRulesMenu: _l("应用的一般规则"),
            titleFilterMenu: _l("过滤数据行的规则"),
            titleColumMenu: _l("生成新列的规则"),
            titleRemoveMapping: _l("移除列定义分配"),
            titleApplyColumnDefinitions: _l("应用这些列定义并返回规则预览"),
            titleErrorOkay: _l("忽略此错误并返回规则构建器，以便尝试新规则"),
            namePlaceholder: _l("输入新集合的名称"),
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
            validityErrorHeader: _l("必须解决以下问题才能继续："),
        };
    },
    computed: {
        returnValidityErrorMessages: function () {
            return this.validityErrorMessages;
        },
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
            if (this.validityErrorMessages.length != 0) {
                return _l("由于验证错误，按钮已禁用。请查看上方的警告。");
            } else if (this.elementsType == "datasets" || this.elementsType == "library_datasets") {
                return _l("从指定的规则和数据集创建新集合");
            } else if (this.elementsType == "collection_contents") {
                return _l("保存规则并返回工具表单");
            } else {
                return _l("使用指定的规则上传集合");
            }
        },
        titleCancel() {
            if (this.importType == "datasets") {
                return _l("关闭此模态窗口，不上传任何数据集");
            } else {
                return _l("关闭此模态窗口，不创建任何集合");
            }
        },
        finishButtonTitle() {
            if (this.elementsType == "datasets" || this.elementsType == "library_datasets") {
                return _l("创建");
            } else if (this.elementsType == "collection_contents") {
                return _l("保存");
            } else {
                return _l("上传");
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
                    // 如果没有约束输入，提供一些不同的选项
                    collectionType = "list:list:list:paired";
                }
                const collectionTypeRanks = collectionType.split(":");
                for (const index in collectionTypeRanks) {
                    const collectionTypeRank = collectionTypeRanks[index];
                    if (collectionTypeRank == "list") {
                        // TODO: 如果是平面列表，则去掉结尾的数字
                        metadataOptions["identifier" + index] = _l("列表标识符 ") + (parseInt(index) + 1);
                    } else {
                        metadataOptions["identifier" + index] = _l("配对标识符");
                    }
                }
                metadataOptions["tags"] = _l("标签");
            } else if (this.elementsType == "ftp") {
                metadataOptions["path"] = _l("路径");
            } else if (this.elementsType == "remote_files") {
                metadataOptions["url"] = _l("URL");
                metadataOptions["url_deferred"] = _l("URL（延迟）");
            } else if (this.elementsType == "library_datasets") {
                metadataOptions["name"] = _l("名称");
            } else if (this.elementsType == "datasets") {
                metadataOptions["hid"] = _l("历史ID（hid）");
                metadataOptions["name"] = _l("名称");
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
        validName() {
            let valid = true;
            const buildingCollection = this.importType == "collections";
            const mappingAsDict = this.mappingAsDict;
            const requiresName =
                buildingCollection && this.elementsType != "collection_contents" && !mappingAsDict.collection_name;
            if (requiresName) {
                valid = this.collectionName.length > 0;
            }
            return valid;
        },
        validRules() {
            let valid = true;
            for (const rule of this.rules) {
                if (rule.error) {
                    valid = false;
                }
            }
            return valid;
        },
        validOnlyOnePath() {
            let valid = true;
            const mappingAsDict = this.mappingAsDict;
            let pathSourceCount = 0;
            if (mappingAsDict.ftp_path) {
                pathSourceCount += 1;
            }
            if (mappingAsDict.url) {
                pathSourceCount += 1;
            }
            if (mappingAsDict.url_deferred) {
                pathSourceCount += 1;
            }
            if (pathSourceCount > 1) {
                // Can only specify one of these.
                valid = false;
            }
            return valid;
        },
        validSourceColumn() {
            let valid = true;
            const mappingAsDict = this.mappingAsDict;
            const requiresSourceColumn =
                this.elementsType == "ftp" || this.elementsType == "raw" || this.elementsType == "remote_files";
            if (requiresSourceColumn && !mappingAsDict.ftp_path && !mappingAsDict.url && !mappingAsDict.url_deferred) {
                valid = false;
            }
            return valid;
        },
        validIdentifierColumns() {
            let valid = true;
            const identifierColumns = this.identifierColumns();
            const buildingCollection = this.importType == "collections";
            if (buildingCollection && identifierColumns.length == 0) {
                valid = false;
            }
            return valid;
        },
        validInput() {
            return (
                this.validName &&
                this.validRules &&
                this.validOnlyOnePath &&
                this.validSourceColumn &&
                this.validIdentifierColumns
            );
        },
        validityErrorMessages() {
            const messages = [];
            if (!this.validName) {
                messages.push("请为集合命名。");
            }
            if (!this.validRules) {
                messages.push("您的规则中存在错误。");
            }
            if (!this.validOnlyOnePath) {
                messages.push("只能指定一个FTP路径或URL。");
            }
            if (!this.validSourceColumn) {
                messages.push("请指定源列（FTP路径或URL）。");
            }
            if (!this.validIdentifierColumns) {
                messages.push("请指定一列作为列表标识符。");
            }
            return messages;
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
    watch: {
        addColumnRegexType: function (val) {
            if (val == "groups") {
                this.addColumnRegexGroupCount = 1;
            }
            if (val == "replacement") {
                this.addColumnRegexReplacement = null;
            }
        },
        addColumnRegexGroupCount: function (oldVal, newVal) {
            if (oldVal != newVal) {
                if (newVal < 1) {
                    this.addColumnRegexGroupCount = 1;
                }
            }
        },
    },created() {
        if (this.elementsType !== "collection_contents") {
            let columnCount = null;
            if (this.elementsType == "datasets") {
                for (const element of this.initialElements) {
                    if (element.history_content_type == "dataset_collection") {
                        this.errorMessage =
                            "此组件只能用于数据集，您指定了一个或多个集合。";
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

            // TODO: 提供者...
            UploadUtils.getUploadDatatypes(false, UploadUtils.AUTO_EXTENSION)
                .then((extensions) => {
                    this.extensions = extensions;
                    this.extension = UploadUtils.DEFAULT_EXTENSION;
                })
                .catch((err) => {
                    console.log("RuleCollectionBuilder 中出错，无法加载数据类型", err);
                });

            // TODO: 提供者...
            UploadUtils.getUploadDbKeys(UploadUtils.DEFAULT_DBKEY)
                .then((dbKeys) => {
                    this.genomes = dbKeys;
                    this.genome = UploadUtils.DEFAULT_DBKEY;
                })
                .catch((err) => {
                    console.log("RuleCollectionBuilder 中出错，无法加载基因组", err);
                });
        }
    },
    mounted() {
        // something bizarre is up with the rendering of hands-on-table, needs a click to render.
        // Vue.nextTick() didn't work here.
        setTimeout(() => {
            this.$refs.hotTable.$el.click();
        }, 200);
    },
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
                if (this.genome !== UploadUtils.DEFAULT_DBKEY) {
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
                this.ruleSourceError = "解析规则时出现了问题.";
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
            startWatchingHistory();
            this.waitOnJob(response);
        },
        waitOnJob(response) {
            const jobId = response.data.jobs[0].id;
            const handleJobShow = (jobResponse) => {
                const state = jobResponse.data.state;
                this.waitingJobState = state;
                if (NON_TERMINAL_STATES.indexOf(state) !== -1) {
                    setTimeout(doJobCheck, 1000);
                } else if (ERROR_STATES.indexOf(state) !== -1) {
                    this.state = "error";
                    this.errorMessage =
                        "运行上传任务时遇到未知错误，这可能是服务器问题或上传定义问题.";
                    this.doFullJobCheck(jobId);
                } else {
                    startWatchingHistory();
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
                    let errorMessage = "在运行上传作业时遇到错误。";
                    if (stderr.indexOf("binary file contains inappropriate content") > -1) {
                        errorMessage +=
                            "问题可能是批量上传器无法像普通上传器那样自动解压您的文件，请指定正确的扩展名或上传已解压的数据。";
                    }
                    errorMessage += "上传作业已完成，但有标准错误输出：" + stderr;
                    this.errorMessage = errorMessage;
                }
            };
            axios.get(`${getAppRoot()}api/jobs/${jobId}?full=True`).then(handleJobShow).catch(this.renderFetchError);
        },
        renderFetchError(error) {
            this.state = "error";
            if (error.response) {
                console.log(error.response);
                this.errorMessage = errorMessageAsString(error);
            } else {
                console.log(error);
                this.errorMessage = "未知错误发生: " + error;
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
                this.errorMessage = "您的规则中有未定义的列.";
                this.state = "error";
                return;
            }
            this.saveSession(JSON.stringify(asJson));
            this.state = "wait";
            const { collectionName: name, collectionType, hideSourceItems } = this;
            if (this.elementsType == "datasets" || this.elementsType == "library_datasets") {
                const elements = this.creationElementsFromDatasets();
                if (this.state !== "error") {
                    const deferreds = Object.entries(elements).map(([name, els]) => {
                        // This looks like a promise but it is not one because creationFn and
                        // oncreate are references to function from the backbone models which means
                        // they are expecting their arguments in a different order. So, looks like,
                        // jQuery.Deferred and therefore jQuery are still dependencies
                        return this.creationFn(els, collectionType, name, hideSourceItems).then(this.oncreate);
                    });
                    const promises = deferreds.map(deferredToPromise);
                    return Promise.all(promises).catch((err) => this.renderFetchError(err));
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
                console.log("错误，但不应该出现这种情况，创建按钮应该被禁用.");
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
                                        "检测到未知的配对状态指示符——仅允许使用 F, R, 1, 2, R1, R2, forward 或 reverse。";
                                    return;
                                }
                            }
                            const element = createDatasetDescription(dataIndex, identifier);
                            elementsAtDepth.push(element);
                            if (identifiersAtDepth.indexOf(identifier) >= 0) {
                                this.state = "error";
                                this.errorMessage = "检测到重复的标识符，集合标识符必须唯一。";
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
            if (mappingAsDict.url || mappingAsDict.url_deferred) {
                let urlColumn;
                if (mappingAsDict.url) {
                    urlColumn = mappingAsDict.url.columns[0];
                } else {
                    urlColumn = mappingAsDict.url_deferred.columns[0];
                }
                let url = data[dataIndex][urlColumn];
                url = url.trim();
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
                if (mappingAsDict.url_deferred) {
                    res["deferred"] = true;
                }
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
};
</script>

<style src="../../node_modules/handsontable/dist/handsontable.full.css"></style>
<style lang="scss">
.rule-collection-builder {
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
        padding: 0px;
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
    .menu-option {
        padding-left: 5px;
    }
    .alert-area li {
        list-style: circle;
        margin-left: 32px;
    }
}
</style>
