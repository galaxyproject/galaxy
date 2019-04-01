import _ from "underscore";
import _l from "utils/localization";
import pyre from "pyre-to-regexp";

const NEW_COLUMN = "new";

const multiColumnsToString = function(targetColumns, colHeaders) {
    if (targetColumns.length == 0) {
        return `no columns`;
    } else if (targetColumns.length == 1) {
        return `column ${colHeaders[targetColumns[0]]}`;
    } else {
        const targetHeaders = targetColumns.map(el => colHeaders[el]);
        // https://stackoverflow.com/questions/16251822/array-to-comma-separated-string-and-for-last-tag-use-the-and-instead-of-comma
        return `columns ${[targetHeaders.slice(0, -1).join(", "), targetHeaders.slice(-1)[0]].join(" and ")}`;
    }
};

const removeColumns = function(columns, targetColumns) {
    const newColumns = [];
    for (let index in columns) {
        if (targetColumns.indexOf(index) === -1) {
            newColumns.push(columns[index]);
        }
    }
    return newColumns;
};

const applyRegex = function(regex, target, data, replacement, groupCount) {
    let regExp;
    try {
        regExp = pyre(String(regex));
    } catch (error) {
        return { error: `Invalid regular expression specified.` };
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
            groupCount = groupCount && parseInt(groupCount);
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
        return { error: `${failedCount} row(s) failed to match specified regular expression.` };
    }
    return { data };
};

const flatMap = (f, xs) => {
    return xs.reduce((acc, x) => acc.concat(f(x)), []);
};

const RULES = {
    add_column_basename: {
        title: _l("Basename of Path of URL"),
        display: (rule, colHeaders) => {
            return `Add column using basename of column ${colHeaders[rule.target_column]}`;
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
        }
    },
    add_column_rownum: {
        title: _l("Row Number"),
        display: (rule, colHeaders) => {
            return `Add column for the current row number.`;
        },
        init: (component, rule) => {
            if (!rule) {
                component.addColumnRownumStart = 1;
            } else {
                component.addColumnRownumStart = rule.start;
            }
        },
        save: (component, rule) => {
            rule.start = parseInt(component.addColumnRownumStart);
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
        }
    },
    add_column_value: {
        title: _l("Fixed Value"),
        display: (rule, colHeaders) => {
            return `Add column for the constant value of ${rule.value}.`;
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
        }
    },
    add_column_metadata: {
        title: _l("Add Column from Metadata"),
        display: (rule, colHeaders) => {
            return `Add column for ${rule.value}.`;
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
                const identifierIndex = parseInt(ruleValue.substring("identifier".length));
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
            } else if (ruleValue == "hid" || ruleValue == "name" || ruleValue == "path") {
                newRow = (row, index) => {
                    const newRow = row.slice();
                    newRow.push(sources[index][ruleValue]);
                    return newRow;
                };
            } else {
                return { error: `Unknown metadata type [${ruleValue}}]` };
            }
            data = data.map(newRow);
            columns.push(NEW_COLUMN);
            return { data, columns };
        }
    },
    add_column_group_tag_value: {
        title: _l("Add Column from Group Tag Value"),
        display: (rule, colHeaders) => {
            return `Add column for value of group tag ${rule.value}.`;
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
                for (let index in tags) {
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
        }
    },
    add_column_regex: {
        title: _l("Using a Regular Expression"),
        display: (rule, colHeaders) => {
            return `Add new column using ${rule.expression} applied to column ${colHeaders[rule.target_column]}`;
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
                component.addColumnRegexGroupCount = rule.group_count;
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
            if (component.addColumnRegexReplacement) {
                rule.replacement = component.addColumnRegexReplacement;
            }
            if (component.addColumnRegexGroupCount) {
                rule.group_count = component.addColumnRegexGroupCount;
            }
        },
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const rval = applyRegex(rule.expression, target, data, rule.replacement, rule.group_count);
            columns.push(NEW_COLUMN);
            rval.columns = columns;
            return rval;
        }
    },
    add_column_concatenate: {
        title: _l("Concatenate Columns"),
        display: (rule, colHeaders) => {
            return `Concatenate column ${colHeaders[rule.target_column_0]} and column ${
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
        }
    },
    add_column_substr: {
        title: _l("Keep or Trim Prefix or Suffix"),
        display: (rule, colHeaders) => {
            const type = rule.substr_type;
            let display;
            if (type == "keep_prefix") {
                display = `Keep only ${rule.length} characters from the start of column ${
                    colHeaders[rule.target_column]
                }`;
            } else if (type == "drop_prefix") {
                display = `Remove ${rule.length} characters from the start of column ${colHeaders[rule.target_column]}`;
            } else if (type == "keep_suffix") {
                display = `Keep only ${rule.length} characters from the end of column ${
                    colHeaders[rule.target_column]
                }`;
            } else {
                display = `Remove ${rule.length} characters from the end of column ${colHeaders[rule.target_column]}`;
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
            rule.length = parseInt(component.addColumnSubstrLength);
            rule.substr_type = component.addColumnSubstrType;
        },
        apply: (rule, data, sources, columns) => {
            const target = rule.target_column;
            const length = rule.length;
            const type = rule.substr_type;
            function newRow(row) {
                const newRow = row.slice();
                const originalValue = row[target];
                let start = 0,
                    end = originalValue.length;
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
        }
    },
    remove_columns: {
        title: _l("Remove Column(s)"),
        display: (rule, colHeaders) => {
            const targetColumns = rule.target_columns;
            return `Remove ${multiColumnsToString(targetColumns, colHeaders)}`;
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
                for (let index in row) {
                    if (targets.indexOf(parseInt(index)) == -1) {
                        newRow.push(row[index]);
                    }
                }
                return newRow;
            }
            data = data.map(newRow);
            columns = removeColumns(columns, targets);
            return { data, columns };
        }
    },
    add_filter_regex: {
        title: _l("Using a Regular Expression"),
        display: (rule, colHeaders) => {
            return `Filter rows using regular expression ${rule.expression} on column ${
                colHeaders[rule.target_column]
            }`;
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
                return { error: `Invalid regular expression specified.` };
            }
            const target = rule.target_column;
            const invert = rule.invert;
            const filterFunction = function(el, index) {
                const row = data[parseInt(index)];
                return regExp.exec(row[target]) ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        }
    },
    add_filter_count: {
        title: _l("First or Last N Rows"),
        display: (rule, colHeaders) => {
            const which = rule.which;
            const invert = rule.invert;
            if (which == "first" && !invert) {
                return `Filter out first ${rule.count} row(s).`;
            } else if (which == "first" && invert) {
                return `Keep only first ${rule.count} row(s).`;
            } else if (which == "last" && !invert) {
                return `Filter out last ${rule.count} row(s).`;
            } else {
                return `Keep only last ${rule.count} row(s).`;
            }
        },
        init: (component, rule) => {
            if (!rule) {
                component.addFilterCountN = 0;
                component.addFilterCountWhich = "first";
                component.addFilterCountInvert = false;
            } else {
                component.addFilterCountN = parseInt(rule.count);
                component.addFilterCountWhich = rule.which;
                component.addFilterCountInvert = rule.inverse;
            }
        },
        save: (component, rule) => {
            rule.count = parseInt(component.addFilterCountN);
            rule.which = component.addFilterCountWhich;
            rule.invert = component.addFilterCountInvert;
        },
        apply: (rule, data, sources, columns) => {
            const count = rule.count;
            const invert = rule.invert;
            const which = rule.which;
            const dataLength = data.length;
            const filterFunction = function(el, index) {
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
        }
    },
    add_filter_empty: {
        title: _l("On Emptiness"),
        display: (rule, colHeaders) => {
            return `Filter rows if no value for column ${colHeaders[rule.target_column]}`;
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
            const filterFunction = function(el, index) {
                const row = data[parseInt(index)];
                return row[target].length ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        }
    },
    add_filter_matches: {
        title: _l("Matching a Supplied Value"),
        display: (rule, colHeaders) => {
            return `Filter rows with value ${rule.value} for column ${colHeaders[rule.target_column]}`;
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
            const filterFunction = function(el, index) {
                const row = data[parseInt(index)];
                return row[target] == value ? !invert : invert;
            };
            sources = sources.filter(filterFunction);
            data = data.filter(filterFunction);
            return { data, sources };
        }
    },
    add_filter_compare: {
        title: _l("By Comparing to a Numeric Value"),
        display: (rule, colHeaders) => {
            return `Filter rows with value ${rule.compare_type} ${rule.value} for column ${
                colHeaders[rule.target_column]
            }`;
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
            const filterFunction = function(el, index) {
                const row = data[parseInt(index)];
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
        }
    },
    sort: {
        title: _l("Sort"),
        display: (rule, colHeaders) => {
            return `Sort on column ${colHeaders[rule.target_column]}`;
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

            sortable.map(zipped => {
                newData.push(zipped[0]);
                newSources.push(zipped[1]);
            });

            return { data: newData, sources: newSources };
        }
    },
    swap_columns: {
        title: _l("Swap Column(s)"),
        display: (rule, colHeaders) => {
            return `Swap ${multiColumnsToString([rule.target_column_0, rule.target_column_1], colHeaders)}`;
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
        }
    },
    split_columns: {
        title: _l("Split Column(s)"),
        display: (rule, colHeaders) => {
            return `Duplicate each row and split up columns`;
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

            const splitRow = function(row) {
                const newRow0 = [],
                    newRow1 = [];
                for (let index in row) {
                    index = parseInt(index);
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
            sources = flatMap(src => [src, src], sources);
            columns = removeColumns(columns, targets0);
            return { data, sources, columns };
        }
    }
};

const MAPPING_TARGETS = {
    list_identifiers: {
        multiple: true,
        label: _l("List Identifier(s)"),
        columnHeader: _l("List Identifier"),
        help: _l(
            "This should be a short description of the replicate, sample name, condition, etc... that describes each level of the list structure."
        ),
        importType: "collections"
    },
    paired_identifier: {
        label: _l("Paired-end Indicator"),
        columnHeader: _l("Paired Indicator"),
        help: _l(
            "This should be set to '1', 'R1', 'forward', 'f', or 'F' to indicate forward reads, and '2', 'r', 'reverse', 'R2', 'R', or 'R2' to indicate reverse reads."
        ),
        importType: "collections"
    },
    collection_name: {
        label: _l("Collection Name"),
        help: _l(
            "If this is set, all rows with the same collection name will be joined into a collection and it is possible to create multiple collections at once."
        ),
        modes: ["raw", "ftp", "datasets", "library_datasets"],
        importType: "collections"
    },
    name_tag: {
        label: _l("Name Tag"),
        help: _l("Add a name tag or hash tag based on the specified column value for imported datasets."),
        importType: "datasets",
        modes: ["raw", "ftp"]
    },
    tags: {
        multiple: true,
        label: _l("General Purpose Tag(s)"),
        help: _l(
            "Add a general purpose tag based on the specified column value, use : to separate key-value pairs if desired. These tags are not propagated to derived datasets the way name and group tags are."
        ),
        modes: ["raw", "ftp", "datasets", "library_datasets"]
    },
    group_tags: {
        multiple: true,
        label: _l("Group Tag(s)"),
        help: _l(
            "Add a group tag based on the specified column value, use : to separate key-value pairs. These tags are propagated to derived datasets and may be useful for factorial experiments."
        ),
        modes: ["raw", "ftp", "datasets", "library_datasets"]
    },
    name: {
        label: _l("Name"),
        importType: "datasets"
    },
    dbkey: {
        label: _l("Genome"),
        modes: ["raw", "ftp"]
    },
    file_type: {
        label: _l("Type"),
        modes: ["raw", "ftp"],
        help: _l("This should be the Galaxy file type corresponding to this file.")
    },
    url: {
        label: _l("URL"),
        modes: ["raw"],
        help: _l("This should be a URL the file can be downloaded from.")
    },
    info: {
        label: _l("Info"),
        help: _l(
            "Unstructured text associated with the dataset that shows up in the history panel, this is optional and can be whatever you would like."
        ),
        modes: ["raw", "ftp"]
    },
    ftp_path: {
        label: _l("FTP Path"),
        modes: ["raw", "ftp"],
        help: _l(
            "This should be the path to the target file to include relative to your FTP directory on the Galaxy server"
        ),
        requiresFtp: true
    }
};

const columnDisplay = function(columns, colHeaders) {
    let columnNames;
    if (typeof columns == "object") {
        columnNames = columns.map(idx => colHeaders[idx]);
    } else {
        columnNames = [colHeaders[columns]];
    }
    if (columnNames.length == 2) {
        return "columns " + columnNames[0] + " and " + columnNames[1];
    } else if (columnNames.length > 2) {
        return "columns " + columnNames.slice(0, -1).join(", ") + ", and " + columnNames[columnNames.length - 1];
    } else {
        return "column " + columnNames[0];
    }
};

const colHeadersFor = function(data, columns) {
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

const applyRules = function(data, sources, columns, rules, headersPerRule = []) {
    let colHeadersPerRule = Array.from(headersPerRule);
    let hasRuleError = false;
    for (var ruleIndex in rules) {
        const ruleHeaders = colHeadersFor(data, columns);
        colHeadersPerRule[ruleIndex] = ruleHeaders;
        const rule = rules[ruleIndex];
        rule.error = null;
        rule.warn = null;
        if (hasRuleError) {
            rule.warn = _l("Skipped due to previous errors.");
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
    MAPPING_TARGETS: MAPPING_TARGETS
};
