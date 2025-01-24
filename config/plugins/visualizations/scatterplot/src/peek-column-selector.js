import $ from "jquery";

//==============================================================================
/** Column selection using the peek display as the control.
 *  Adds rows to the bottom of the peek with clickable areas in each cell
 *      to allow the user to select columns.
 *  Column selection can be limited to a single column or multiple.
 *  (Optionally) adds a left hand column of column selection prompts.
 *  (Optionally) allows the column headers to be clicked/renamed
 *      and set to some initial value.
 *  (Optionally) hides comment rows.
 *  (Optionally) allows pre-selecting and disabling certain columns for
 *      each row control.
 *
 *  Construct by selecting a peek table to be used with jQuery and
 *      calling 'peekColumnSelector' with options.
 *  Options must include a 'controls' array and can include other options
 *      listed below.
 *  @example:
 *  $( 'pre.peek' ).peekColumnSelector({
 *          columnNames : ["Chromosome", "Start", "Base", "", "", "Qual" ],
 *          controls : [
 *              { label: 'X Column',  id: 'xColumn' },
 *              { label: 'Y Column',  id: 'yColumn', selected: 2 },
 *              { label: 'ID Column', id: 'idColumn', selected: 4, disabled: [ 1, 5 ] },
 *              { label: 'Heatmap',   id: 'heatmap', selected: [ 2, 4 ], disabled: [ 0, 1 ], multiselect: true,
 *                selectedText: 'Included', unselectedText: 'Excluded' }
 *          ],
 *          renameColumns       : true,
 *          hideCommentRows     : true,
 *          includePrompts      : true,
 *          topLeftContent      : 'Data sample:'
 *      }).on( 'peek-column-selector.change', function( ev, selection ){
 *          console.info( 'new selection:', selection );
 *          //{ yColumn: 2 }
 *      }).on( 'peek-column-selector.rename', function( ev, names ){
 *          console.info( 'column names', names );
 *          //[ 'Bler', 'Start', 'Base', '', '', 'Qual' ]
 *      });
 *
 *  An event is fired when column selection is changed and the event
 *      is passed an object in the form: { the row id : the new selection value }.
 *  An event is also fired when the table headers are re-named and
 *      is passed the new array of column names.
 */

/** option defaults */
var defaults = {
    /** does this control allow renaming headers? */
    renameColumns: false,
    /** does this control allow renaming headers? */
    columnNames: [],
    /** the comment character used by the peek's datatype */
    commentChar: "#",
    /** should comment rows be shown or hidden in the peek */
    hideCommentRows: false,
    /** should a column of row control prompts be used */
    includePrompts: true,
    /** what is the content of the top left cell (often a title) */
    topLeftContent: "Columns:",
};

/** class added to the pre.peek element (to allow css on just the control) */
const PEEKCONTROL_CLASS = "peek-column-selector";

/** the string of the event fired when a control row changes */
const CHANGE_EVENT = "peek-column-selector.change";

/** the string of the event fired when a column is renamed */
const RENAME_EVENT = "peek-column-selector.rename";

/** class added to the control rows */
const ROW_CLASS = "control";

/** class added to the left-hand cells that serve as row prompts */
const PROMPT_CLASS = "control-prompt";

/** class added to selected _cells_/tds */
const SELECTED_CLASS = "selected";

/** class added to disabled/un-clickable cells/tds */
const DISABLED_CLASS = "disabled";

/** class added to the clickable surface within a cell to select it */
const BUTTON_CLASS = "button";

/** class added to peek table header (th) cells to indicate they can be clicked and are renamable */
const RENAMABLE_HEADER_CLASS = "renamable-header";

/** the data key used for each cell to store the column index ('data-...') */
const COLUMN_INDEX_DATA_KEY = "column-index";

/** renamable header data key used to store the column name (w/o the number and dot: '1.Bler') */
const COLUMN_NAME_DATA_KEY = "column-name";

//TODO: not happy with pure functional here - rows should polymorph (multi, single, etc.)
//TODO: needs clean up, move handlers to outer scope

// ........................................................................
/** validate the control data sent in for each row */
function validateControl(control) {
    if (control.disabled && $.type(control.disabled) !== "array") {
        throw new Error(`"disabled" must be defined as an array of indeces: ${JSON.stringify(control)}`);
    }
    if (control.multiselect && control.selected && $.type(control.selected) !== "array") {
        throw new Error(`Mulitselect rows need an array for "selected": ${JSON.stringify(control)}`);
    }
    if (!control.label || !control.id) {
        throw new Error(`Peek controls need a label and id for each control row: ${JSON.stringify(control)}`);
    }
    if (control.disabled && control.disabled.indexOf(control.selected) !== -1) {
        throw new Error(`Selected column is in the list of disabled columns: ${JSON.stringify(control)}`);
    }
    return control;
}

/** build the inner control surface (i.e. button-like) */
function buildButton(control, columnIndex) {
    return $("<div/>").addClass(BUTTON_CLASS).text(control.label);
}

/** build the basic (shared) cell structure */
function buildControlCell(control, columnIndex) {
    var $td = $("<td/>").html(buildButton(control, columnIndex)).attr(`data-${COLUMN_INDEX_DATA_KEY}`, columnIndex);

    // disable if index in disabled array
    if (control.disabled && control.disabled.indexOf(columnIndex) !== -1) {
        $td.addClass(DISABLED_CLASS);
    }
    return $td;
}

/** set the text of the control based on selected/un */
function setSelectedText($cell, control, columnIndex) {
    var $button = $cell.children(`.${BUTTON_CLASS}`);
    if ($cell.hasClass(SELECTED_CLASS)) {
        $button.html(control.selectedText !== undefined ? control.selectedText : control.label);
    } else {
        $button.html(control.unselectedText !== undefined ? control.unselectedText : control.label);
    }
}

/** build a cell for a row that only allows one selection */
function buildSingleSelectCell(control, columnIndex) {
    // only one selection - selected is single index
    var $cell = buildControlCell(control, columnIndex);
    if (control.selected === columnIndex) {
        $cell.addClass(SELECTED_CLASS);
    }
    setSelectedText($cell, control, columnIndex);

    // only add the handler to non-disabled controls
    if (!$cell.hasClass(DISABLED_CLASS)) {
        $cell.click(function selectClick(ev) {
            var $cell = $(this);
            // don't re-select or fire event if already selected
            if (!$cell.hasClass(SELECTED_CLASS)) {
                // only one can be selected - remove selected on all others, add it here
                var $otherSelected = $cell.parent().children(`.${SELECTED_CLASS}`).removeClass(SELECTED_CLASS);
                $otherSelected.each(function () {
                    setSelectedText($(this), control, columnIndex);
                });

                $cell.addClass(SELECTED_CLASS);
                setSelectedText($cell, control, columnIndex);

                // fire the event from the table itself, passing the id and index of selected
                var eventData = {};

                var key = $cell.parent().attr("id");
                eventData[key] = $cell.data(COLUMN_INDEX_DATA_KEY);
                $cell.parents(".peek").trigger(CHANGE_EVENT, eventData);
            }
        });
    }
    return $cell;
}

/** build a cell for a row that allows multiple selections */
function buildMultiSelectCell(control, columnIndex) {
    var $cell = buildControlCell(control, columnIndex);
    // multiple selection - selected is an array
    if (control.selected && control.selected.indexOf(columnIndex) !== -1) {
        $cell.addClass(SELECTED_CLASS);
    }
    setSelectedText($cell, control, columnIndex);

    // only add the handler to non-disabled controls
    if (!$cell.hasClass(DISABLED_CLASS)) {
        $cell.click(function multiselectClick(ev) {
            var $cell = $(this);
            // can be more than one selected - toggle selected on this cell
            $cell.toggleClass(SELECTED_CLASS);
            setSelectedText($cell, control, columnIndex);
            var selectedColumnIndeces = $cell
                .parent()
                .find(`.${SELECTED_CLASS}`)
                .map((i, e) => $(e).data(COLUMN_INDEX_DATA_KEY));

            // fire the event from the table itself, passing the id and index of selected
            var eventData = {};

            var key = $cell.parent().attr("id");
            eventData[key] = $.makeArray(selectedColumnIndeces);
            $cell.parents(".peek").trigger(CHANGE_EVENT, eventData);
        });
    }
    return $cell;
}

/** iterate over columns in peek and create a control for each */
function buildControlCells(count, control) {
    var $cells = [];
    // build a control for each column - using a build fn based on control
    for (var columnIndex = 0; columnIndex < count; columnIndex += 1) {
        $cells.push(
            control.multiselect
                ? buildMultiSelectCell(control, columnIndex)
                : buildSingleSelectCell(control, columnIndex)
        );
    }
    return $cells;
}

/** build a row of controls for the peek */
function buildControlRow(cellCount, control, includePrompts) {
    var $controlRow = $("<tr/>").attr("id", control.id).addClass(ROW_CLASS);
    if (includePrompts) {
        var $promptCell = $("<td/>").addClass(PROMPT_CLASS).text(`${control.label}:`);
        $controlRow.append($promptCell);
    }
    $controlRow.append(buildControlCells(cellCount, control));
    return $controlRow;
}

// ........................................................................
/** add to the peek, using options for configuration, return the peek */
function peekColumnSelector(options) {
    options = $.extend(true, {}, defaults, options);

    var $peek = $(this).addClass(PEEKCONTROL_CLASS);
    var $peektable = $peek.find("table");

    var // get the size of the tables - width and height, number of comment rows
        columnCount = $peektable.find("th").length;

    var rowCount = $peektable.find("tr").length;

    var // get the rows containing text starting with the comment char (also make them grey)
        $commentRows = $peektable.find("td[colspan]").map(function (e, i) {
            var $this = $(this);
            if ($this.text() && $this.text().match(new RegExp(`^${options.commentChar}`))) {
                return $(this).css("color", "grey").parent().get(0);
            }
            return null;
        });

    // should comment rows in the peek be hidden?
    if (options.hideCommentRows) {
        $commentRows.hide();
        rowCount -= $commentRows.length;
    }
    //console.debug( 'rowCount:', rowCount, 'columnCount:', columnCount, '$commentRows:', $commentRows );

    // should a first column of control prompts be added?
    if (options.includePrompts) {
        var $topLeft = $("<th/>").addClass("top-left").text(options.topLeftContent).attr("rowspan", rowCount);
        $peektable.find("tr").first().prepend($topLeft);
    }

    // save either the options column name or the parsed text of each column header in html5 data attr and text
    var $headers = $peektable.find("th:not(.top-left)").each(function (i, e) {
        var $this = $(this);

        var // can be '1.name' or '1'
            text = $this.text().replace(/^\d+\.*/, "");

        var name = options.columnNames[i] || text;
        $this.attr(`data-${COLUMN_NAME_DATA_KEY}`, name).text(i + 1 + (name ? `.${name}` : ""));
    });

    // allow renaming of columns when the header is clicked
    if (options.renameColumns) {
        $headers.addClass(RENAMABLE_HEADER_CLASS).click(function renameColumn() {
            // prompt for new name
            var $this = $(this);

            var index = $this.index() + (options.includePrompts ? 0 : 1);
            var prevName = $this.data(COLUMN_NAME_DATA_KEY);
            var newColumnName = window.prompt("New column name:", prevName);
            if (newColumnName !== null && newColumnName !== prevName) {
                // set the new text and data
                $this
                    .text(index + (newColumnName ? `.${newColumnName}` : ""))
                    .data(COLUMN_NAME_DATA_KEY, newColumnName)
                    .attr("data-", COLUMN_NAME_DATA_KEY, newColumnName);
                // fire event for new column names
                var columnNames = $.makeArray(
                    $this
                        .parent()
                        .children("th:not(.top-left)")
                        .map(function () {
                            return $(this).data(COLUMN_NAME_DATA_KEY);
                        })
                );
                $this.parents(".peek").trigger(RENAME_EVENT, columnNames);
            }
        });
    }

    // build a row for each control
    options.controls.forEach((control, i) => {
        validateControl(control);
        var $controlRow = buildControlRow(columnCount, control, options.includePrompts);
        $peektable.find("tbody").append($controlRow);
    });
    return this;
}

// ........................................................................
// as jq plugin
$.fn.extend({
    peekColumnSelector: function $peekColumnSelector(options) {
        return this.map(function () {
            return peekColumnSelector.call(this, options);
        });
    },
});
