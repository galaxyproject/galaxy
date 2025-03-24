import pyre from "pyre-to-regexp";
import _ from "underscore";
import _l from "utils/localization";
const NEW_COLUMN = "new";

const multiColumnsToString = function (targetColumns, colHeaders) {
    if (targetColumns.length == 0) {
        return `无列`;
    } else if (targetColumns.length == 1) {
        return `列 ${colHeaders[targetColumns[0]]}`;
    } else {
        const targetHeaders = targetColumns.map((el) => colHeaders[el]);
        // https://stackoverflow.com/questions/16251822/array-to-comma-separated-string-and-for-last-tag-use-the-and-instead-of-comma
        return `列 ${[targetHeaders.slice(0, -1).join("、"), targetHeaders.slice(-1)[0]].join(" 和 ")}`;
    }
};

const removeColumns = function (columns, targetColumns) {
    const newColumns = [];
    for (const index in columns) {
        if (targetColumns.indexOf(index) === -1) {
            newColumns.push(columns[index]);
        }
    }
    return newColumns;
};

const applyRegex = function (regex, target, data, replacement, groupCount) {
    let regExp;
    try {
        regExp = pyre(String(regex));
    } catch (error) {
        return { error: `指定的正则表达式无效。` };
    }
    let failedCount = 0;
    function newRow(row) {
        const source = row[target];
        const match = regExp.exec(source);
        if (!match) {
            failedCount++;
            return null;
        }
        if (!replacement) {
            groupCount = groupCount && parseInt(groupCount, 10);
            if (groupCount) {
                if (match.length != groupCount + 1) {
                    failedCount++;
                    return null;
                }
                return row.concat(match.splice(1, match.length));
            } else {
                return row.concat([match[0]]);
            }
        } else {
            return row.concat([regExp.pyreReplace(match[0], replacement)]);
        }
    }
    data = data.map(newRow);
    if (failedCount > 0) {
        return { error: `${failedCount} 行数据未能匹配指定的正则表达式。` };
    }
    return { data };
};

const flatMap = (f, xs) => {
    return xs.reduce((acc, x) => acc.concat(f(x)), []);
};

const RULES = {
    add_column_basename: {
        title: _l("路径或URL的基础名称"),
        display: (rule, colHeaders) => {
            return `使用列 ${colHeaders[rule.target_column]} 的基础名称添加列`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnBasenameTarget = 0;
            } else {
                component.addColumnBasenameTarget = rule.target_column;
            }
        },
        save: (component, rule) => {
            rule.target_column = component.addColumnBasenameTarget;
        },
        apply: (rule, data, sources, columns) => {
            // https://github.com/kgryte/regex-basename-posix/blob/master/lib/index.js
            //const re = /^(?:\/?|)(?:[\s\S]*?)((?:\.{1,2}|[^\/]+?|)(?:\.[^.\/]*|))(?:[\/]*)$/;
            // https://stackoverflow.com/questions/8376525/get-value-of-a-string-after-a-slash-in-javascript
            const re = "[^/]*$";
            const target = rule.target_column;
            const rval = applyRegex(re, target, data);
            columns.push(NEW_COLUMN);
            rval.columns = columns;
            return rval;
        },
    },
    add_column_rownum: {
        title: _l("行号"),
        display: (rule, colHeaders) => {
            return `添加当前行号列。`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnRownumStart = 1;
            } else {
                component.addColumnRownumStart = rule.start;
            }
        },
        save: (component, rule) => {
            rule.start = parseInt(component.addColumnRownumStart, 10);
        },
        apply: (rule, data, sources, columns) => {
            let rownum = rule.start;
            function newRow(row) {
                const newRow = row.slice();
                newRow.push(String(rownum));
                rownum += 1;
                return newRow;
            }
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data, columns };
        },
    },
    add_column_value: {
        title: _l("固定值"),
        display: (rule, colHeaders) => {
            return `添加常量值 ${rule.value} 的列。`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnValue = "";
            } else {
                component.addColumnValue = rule.value;
            }
        },
        save: (component, rule) => {
            rule.value = component.addColumnValue;
        },
        apply: (rule, data, sources, columns) => {
            const addValue = rule.value;
            function newRow(row) {
                const newRow = row.slice();
                newRow.push(addValue);
                return newRow;
            }
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data, columns };
        },
    },
    add_column_metadata: {
        title: _l("从元数据添加列"),
        display: (rule, colHeaders) => {
            return `为 ${rule.value} 添加列。`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnMetadataValue = null;
            } else {
                component.addColumnMetadataValue = rule.value;
            }
        },
        save: (component, rule) => {
            rule.value = component.addColumnMetadataValue;
        },
        apply: (rule, data, sources, columns) => {
            const ruleValue = rule.value;
            let newRow;
            if (ruleValue.indexOf("identifier") == 0) {
                const identifierIndex = parseInt(ruleValue.substring("identifier".length), 10);
                newRow = (row, index) => {
                    const newRow = row.slice();
                    newRow.push(sources[index]["identifiers"][identifierIndex]);
                    return newRow;
                };
            } else if (ruleValue == "tags") {
                newRow = (row, index) => {
                    const newRow = row.slice();
                    const tags = sources[index]["tags"];
                    tags.sort();
                    newRow.push(tags.join(","));
                    return newRow;
                };
            } else if (ruleValue == "hid" || ruleValue == "name" || ruleValue == "path" || ruleValue == "uri") {
                newRow = (row, index) => {
                    const newRow = row.slice();
                    newRow.push(sources[index][ruleValue]);
                    return newRow;
                };
            } else {
                return { error: `未知的元数据类型 [${ruleValue}]` };
            }
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data, columns };
        },
    },
    add_column_group_tag_value: {
        title: _l("从组标签值添加列"),
        display: (rule, colHeaders) => {
            return `为组标签 ${rule.value} 的值添加列。`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnGroupTagValueValue = null;
                component.addColumnGroupTagValueDefault = "";
            } else {
                component.addColumnGroupTagValueValue = rule.value;
                component.addColumnGroupTagValueDefault = rule.default_value;
            }
        },
        save: (component, rule) => {
            rule.value = component.addColumnGroupTagValueValue;
            rule.default_value = component.addColumnGroupTagValueDefault;
        },
        apply: (rule, data, sources, columns) => {
            const ruleValue = rule.value;
            const groupTagPrefix = `group:${ruleValue}:`;
            const newRow = (row, index) => {
                const newRow = row.slice();
                const tags = sources[index]["tags"];
                tags.sort();
                let groupTagValue = rule.default_value;
                for (const index in tags) {
                    const tag = tags[index];
                    if (tag.indexOf(groupTagPrefix) == 0) {
                        groupTagValue = tag.substr(groupTagPrefix.length);
                        break;
                    }
                }
                newRow.push(groupTagValue);
                return newRow;
            };
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data, columns };
        },
    },
    add_column_regex: {
        title: _l("使用正则表达式"),
        display: (rule, colHeaders) => {
            return `使用 ${rule.expression} 应用于列 ${colHeaders[rule.target_column]} 添加新列`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnRegexTarget = 0;
                component.addColumnRegexExpression = "";
                component.addColumnRegexReplacement = null;
                component.addColumnRegexGroupCount = null;
            } else {
                component.addColumnRegexTarget = rule.target_column;
                component.addColumnRegexExpression = rule.expression;
                component.addColumnRegexReplacement = rule.replacement;
                component.addColumnRegexGroupCount = parseInt(rule.group_count);
            }
            let addColumnRegexType = "global";
            if (component.addColumnRegexGroupCount) {
                addColumnRegexType = "groups";
            } else if (component.addColumnRegexReplacement) {
                addColumnRegexType = "replacement";
            }
            component.addColumnRegexType = addColumnRegexType;
        },
        save: (component, rule) => {
            rule.target_column = component.addColumnRegexTarget;
            rule.expression = component.addColumnRegexExpression;
            if (component.addColumnRegexType == "replacement" && component.addColumnRegexReplacement) {
                rule.replacement = component.addColumnRegexReplacement;
                rule.group_count = null;
            } else if (component.addColumnRegexType == "groups" && component.addColumnRegexGroupCount) {
                rule.group_count = parseInt(component.addColumnRegexGroupCount);
                rule.replacement = null;
            } else if (component.addColumnRegexType == "global") {
                rule.replacement = null;
                rule.group_count = null;
            }
        },
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const rval = applyRegex(rule.expression, target, data, rule.replacement, rule.group_count);
            if (rule.group_count) {
                for (let i = 0; i < rule.group_count; i++) {
                    columns.push(NEW_COLUMN);
                }
            } else {
                columns.push(NEW_COLUMN);
            }
            rval.columns = columns;
            return rval;
        },
    },
    add_column_concatenate: {
        title: _l("连接列"),
        display: (rule, colHeaders) => {
            return `连接列 ${colHeaders[rule.target_column_0]} 和列 ${
                colHeaders[rule.target_column_1]
            }`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const target0 = rule.target_column_0;
            const target1 = rule.target_column_1;
            function newRow(row) {
                const newRow = row.slice();
                newRow.push(row[target0] + row[target1]);
                return newRow;
            }
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data, columns };
        },
    },
    add_column_substr: {
        title: _l("保留或裁剪前缀或后缀"),
        display: (rule, colHeaders) => {
            const type = rule.substr_type;
            let display;
            if (type == "keep_prefix") {
                display = `仅保留列 ${colHeaders[rule.target_column]} 开始的 ${rule.length} 个字符`;
            } else if (type == "drop_prefix") {
                display = `从列 ${colHeaders[rule.target_column]} 开始处删除 ${rule.length} 个字符`;
            } else if (type == "keep_suffix") {
                display = `仅保留列 ${colHeaders[rule.target_column]} 末尾的 ${rule.length} 个字符`;
            } else {
                display = `从列 ${colHeaders[rule.target_column]} 末尾删除 ${rule.length} 个字符`;
            }
            return display;
        },
        init: (component, rule) => {
            if (!rule) {
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
            rule.length = parseInt(component.addColumnSubstrLength, 10);
            rule.substr_type = component.addColumnSubstrType;
        },
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const length = rule.length;
            const type = rule.substr_type;
            function newRow(row) {
                const newRow = row.slice();
                const originalValue = row[target];
                let start = 0;
                let end = originalValue.length;
                if (type == "keep_prefix") {
                    end = length;
                } else if (type == "drop_prefix") {
                    start = length;
                } else if (type == "keep_suffix") {
                    start = end - length;
                    if (start < 0) {
                        start = 0;
                    }
                } else {
                    end = end - length;
                    if (end < 0) {
                        end = 0;
                    }
                }
                newRow.push(originalValue.substr(start, end));
                return newRow;
            }
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data };
        },
    },
    remove_columns: {
        title: _l("删除列"),
        display: (rule, colHeaders) => {
            const targetColumns = rule.target_columns;
            return `删除 ${multiColumnsToString(targetColumns, colHeaders)}`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.removeColumnTargets = [];
            } else {
                component.removeColumnTargets = rule.target_columns;
            }
        },
        save: (component, rule) => {
            rule.target_columns = component.removeColumnTargets;
        },
        apply: (rule, data, sources, columns) => {
            const targets = rule.target_columns;
            function newRow(row) {
                const newRow = [];
                for (const index in row) {
                    if (targets.indexOf(parseInt(index, 10)) == -1) {
                        newRow.push(row[index]);
                    }
                }
                return newRow;
            }
            data = data.map(newRow);
            columns = removeColumns(columns, targets);
            return { data, columns };
        },
    },
    add_filter_regex: {
        title: _l("使用正则表达式"),
        display: (rule, colHeaders) => {
            return `使用列 ${colHeaders[rule.target_column]} 上的正则表达式 ${rule.expression} 过滤行`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const regex = String(rule.expression);
            var regExp;
            try {
                regExp = pyre(regex);
            } catch (error) {
                return { error: `指定的正则表达式无效。` };
            }
            const target = rule.target_column;
            const invert = rule.invert;
            const filterFunction = function (el, index) {
                const row = data[parseInt(index, 10)];
                return regExp.exec(row[target]) ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        },
    },
    add_filter_count: {
        title: _l("前N行或后N行"),
        display: (rule, colHeaders) => {
            const which = rule.which;
            const invert = rule.invert;
            if (which == "first" && !invert) {
                return `过滤掉前 ${rule.count} 行。`;
            } else if (which == "first" && invert) {
                return `仅保留前 ${rule.count} 行。`;
            } else if (which == "last" && !invert) {
                return `过滤掉后 ${rule.count} 行。`;
            } else {
                return `仅保留后 ${rule.count} 行。`;
            }
        },
        init: (component, rule) => {
            if (!rule) {
                component.addFilterCountN = 0;
                component.addFilterCountWhich = "first";
                component.addFilterCountInvert = false;
            } else {
                component.addFilterCountN = parseInt(rule.count, 10);
                component.addFilterCountWhich = rule.which;
                component.addFilterCountInvert = rule.inverse;
            }
        },
        save: (component, rule) => {
            rule.count = parseInt(component.addFilterCountN, 10);
            rule.which = component.addFilterCountWhich;
            rule.invert = component.addFilterCountInvert;
        },
        apply: (rule, data, sources, columns) => {
            const count = rule.count;
            const invert = rule.invert;
            const which = rule.which;
            const dataLength = data.length;
            const filterFunction = function (el, index) {
                let matches;
                if (which == "first") {
                    matches = index >= count;
                } else {
                    matches = index < dataLength - count;
                }
                return matches ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        },
    },
    add_filter_empty: {
        title: _l("基于空值"),
        display: (rule, colHeaders) => {
            return `如果列 ${colHeaders[rule.target_column]} 无值则过滤行`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const invert = rule.invert;
            const filterFunction = function (el, index) {
                const row = data[parseInt(index, 10)];
                return row[target].length ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        },
    },
    add_filter_matches: {
        title: _l("匹配提供的值"),
        display: (rule, colHeaders) => {
            return `对列 ${colHeaders[rule.target_column]} 值为 ${rule.value} 的行进行过滤`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const invert = rule.invert;
            const value = rule.value;
            const filterFunction = function (el, index) {
                const row = data[parseInt(index, 10)];
                return row[target] == value ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        },
    },
    add_filter_compare: {
        title: _l("通过与数值比较"),
        display: (rule, colHeaders) => {
            return `对列 ${colHeaders[rule.target_column]} 值 ${rule.compare_type} ${rule.value} 的行进行过滤`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const compare_type = rule.compare_type;
            const value = rule.value;
            const filterFunction = function (el, index) {
                const row = data[parseInt(index, 10)];
                const targetValue = parseFloat(row[target]);
                let matches;
                if (compare_type == "less_than") {
                    matches = targetValue < value;
                } else if (compare_type == "less_than_equal") {
                    matches = targetValue <= value;
                } else if (compare_type == "greater_than") {
                    matches = targetValue > value;
                } else if (compare_type == "greater_than_equal") {
                    matches = targetValue >= value;
                }
                return matches;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        },
    },
    sort: {
        title: _l("排序"),
        display: (rule, colHeaders) => {
            return `按列 ${colHeaders[rule.target_column]} 排序`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const numeric = rule.numeric;

            const sortable = _.zip(data, sources);

            const sortFunc = (a, b) => {
                let aVal = a[0][target];
                let bVal = b[0][target];
                if (numeric) {
                    aVal = parseFloat(aVal);
                    bVal = parseFloat(bVal);
                }
                if (aVal < bVal) {
                    return -1;
                } else if (bVal < aVal) {
                    return 1;
                } else {
                    return 0;
                }
            };

            sortable.sort(sortFunc);

            const newData = [];
            const newSources = [];

            sortable.map((zipped) => {
                newData.push(zipped[0]);
                newSources.push(zipped[1]);
            });

            return { data: newData, sources: newSources };
        },
    },
    swap_columns: {
        title: _l("交换列"),
        display: (rule, colHeaders) => {
            return `交换 ${multiColumnsToString([rule.target_column_0, rule.target_column_1], colHeaders)}`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const target0 = rule.target_column_0;
            const target1 = rule.target_column_1;
            function newRow(row) {
                const newRow = row.slice();
                newRow[target0] = row[target1];
                newRow[target1] = row[target0];
                return newRow;
            }
            data = data.map(newRow);
            const tempColumn = columns[target0];
            columns[target0] = columns[target1];
            columns[target1] = tempColumn;
            return { data, columns };
        },
    },
    split_columns: {
        title: _l("分割列"),
        display: (rule, colHeaders) => {
            return `复制每行并分割列`;
        },
        init: (component, rule) => {
            if (!rule) {
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
        apply: (rule, data, sources, columns) => {
            const targets0 = rule.target_columns_0;
            const targets1 = rule.target_columns_1;

            const splitRow = function (row) {
                const newRow0 = [];
                const newRow1 = [];
                for (let index in row) {
                    index = parseInt(index, 10);
                    if (targets0.indexOf(index) > -1) {
                        newRow0.push(row[index]);
                    } else if (targets1.indexOf(index) > -1) {
                        newRow1.push(row[index]);
                    } else {
                        newRow0.push(row[index]);
                        newRow1.push(row[index]);
                    }
                }
                return [newRow0, newRow1];
            };
            data = flatMap(splitRow, data);
            sources = flatMap((src) => [src, src], sources);
            columns = removeColumns(columns, targets0);
            return { data, sources, columns };
        },
    },
};

const MAPPING_TARGETS = {
    list_identifiers: {
        multiple: true,
        label: _l("列表标识符"),
        columnHeader: _l("列表标识符"),
        help: _l(
            "这应该是描述副本、样本名称、条件等的简短描述，用于描述列表结构的每个级别。"
        ),
        importType: "collections",
    },
    paired_identifier: {
        label: _l("双端指示器"),
        columnHeader: _l("配对指示器"),
        help: _l(
            "这应设置为'1'、'R1'、'forward'、'f'或'F'表示正向读取，'2'、'r'、'reverse'、'R2'、'R'或'R2'表示反向读取。"
        ),
        importType: "collections",
    },
    collection_name: {
        label: _l("集合名称"),
        help: _l(
            "如果设置了此项，所有具有相同集合名称的行将被合并到一个集合中，同时可以创建多个集合。"
        ),
        modes: ["raw", "ftp", "datasets", "library_datasets"],
        importType: "collections",
    },
    name_tag: {
        label: _l("名称标签"),
        help: _l("为导入的数据集根据指定的列值添加名称标签或哈希标签。"),
        importType: "datasets",
        modes: ["raw", "ftp"],
    },
    tags: {
        multiple: true,
        label: _l("通用标签"),
        help: _l(
            "根据指定的列值添加通用标签，使用:分隔键值对（如需要）。这些标签不会像名称和组标签那样被传播到衍生数据集。"
        ),
        modes: ["raw", "ftp", "datasets", "library_datasets", "collection_contents"],
    },
    group_tags: {
        multiple: true,
        label: _l("组标签"),
        help: _l(
            "根据指定的列值添加组标签，使用:分隔键值对。这些标签会被传播到衍生数据集，对于因子实验可能很有用。"
        ),
        modes: ["raw", "ftp", "datasets", "library_datasets", "collection_contents"],
    },
    name: {
        label: _l("名称"),
        importType: "datasets",
    },
    dbkey: {
        label: _l("基因组"),
        modes: ["raw", "ftp"],
    },
    file_type: {
        label: _l("类型"),
        modes: ["raw", "ftp"],
        help: _l("这应该是与此文件对应的Galaxy文件类型。"),
    },
    url: {
        label: _l("URL"),
        modes: ["raw"],
        help: _l("这应该是可以下载文件的URL（或Galaxy识别的URI）。"),
    },
    url_deferred: {
        label: _l("延迟URL"),
        modes: ["raw"],
        help: _l(
            "这应该是可以下载文件的URL（或Galaxy识别的URI）- 文件只有在被工具使用时才会下载。"
        ),
    },
    info: {
        label: _l("信息"),
        help: _l(
            "与数据集关联的非结构化文本，会显示在历史面板中，这是可选的，可以是您想要的任何内容。"
        ),
        modes: ["raw", "ftp"],
    },
    ftp_path: {
        label: _l("FTP路径"),
        modes: ["raw", "ftp"],
        help: _l(
            "这应该是相对于Galaxy服务器上您的FTP目录的目标文件的路径"
        ),
        requiresFtp: true,
    },
};

const columnDisplay = function (columns, colHeaders) {
    let columnNames;
    if (typeof columns == "object") {
        columnNames = columns.map((idx) => colHeaders[idx]);
    } else {
        columnNames = [colHeaders[columns]];
    }
    if (columnNames.length == 2) {
        return "列 " + columnNames[0] + " 和 " + columnNames[1];
    } else if (columnNames.length > 2) {
        return "列 " + columnNames.slice(0, -1).join("、") + " 和 " + columnNames[columnNames.length - 1];
    } else {
        return "列 " + columnNames[0];
    }
};

const colHeadersFor = function (data, columns) {
    if (data.length == 0) {
        if (columns) {
            return columns.map((el, i) => String.fromCharCode(65 + i));
        } else {
            return [];
        }
    } else {
        return data[0].map((el, i) => String.fromCharCode(65 + i));
    }
};

const applyRules = function (data, sources, columns, rules, headersPerRule = []) {
    const colHeadersPerRule = Array.from(headersPerRule);
    let hasRuleError = false;
    for (var ruleIndex in rules) {
        colHeadersPerRule[ruleIndex] = colHeadersFor(data, columns);
        const rule = rules[ruleIndex];
        rule.error = null;
        rule.warn = null;
        if (hasRuleError) {
            rule.warn = _l("由于先前的错误而跳过。");
            continue;
        }
        var ruleType = rule.type;
        const ruleDef = RULES[ruleType];
        const res = ruleDef.apply(rule, data, sources, columns);
        if (res.error) {
            hasRuleError = true;
            rule.error = res.error;
        } else {
            if (res.warn) {
                rule.warn = res.warn;
            }
            data = res.data || data;
            sources = res.sources || sources;
            columns = res.columns || columns;
        }
    }
    return { data, sources, columns, colHeadersPerRule };
};

export default {
    applyRules: applyRules,
    columnDisplay: columnDisplay,
    colHeadersFor: colHeadersFor,
    RULES: RULES,
    MAPPING_TARGETS: MAPPING_TARGETS,
};

export { MAPPING_TARGETS, RULES };
