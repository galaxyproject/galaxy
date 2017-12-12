define("mvc/history/copy-dialog", ["exports", "mvc/ui/ui-modal", "mvc/ui/error-modal", "utils/localization"], function(exports, _uiModal, _errorModal, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _uiModal2 = _interopRequireDefault(_uiModal);

    var _errorModal2 = _interopRequireDefault(_errorModal);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    //==============================================================================
    /**
     * A dialog/modal that allows copying a user history or 'importing' from user
     * another. Generally called via historyCopyDialog below.
     * @type {Object}
     */
    var CopyDialog = {
        // language related strings/fns
        defaultName: _.template("Copy of '<%- name %>'"),
        title: _.template((0, _localization2.default)("Copying history") + " \"<%- name %>\""),
        submitLabel: (0, _localization2.default)("Copy"),
        errorMessage: (0, _localization2.default)("History could not be copied."),
        progressive: (0, _localization2.default)("Copying history"),
        activeLabel: (0, _localization2.default)("Copy only the active, non-deleted datasets"),
        allLabel: (0, _localization2.default)("Copy all datasets including deleted ones"),
        anonWarning: (0, _localization2.default)("As an anonymous user, unless you login or register, you will lose your current history ") + (0, _localization2.default)("after copying this history. "),

        // template for modal body
        _template: _.template([
            //TODO: remove inline styles
            // show a warning message for losing current to anon users
            "<% if( isAnon ){ %>", '<div class="warningmessage">', "<%- anonWarning %>", (0, _localization2.default)("You can"), ' <a href="/user/login">', (0, _localization2.default)("login here"), "</a> ", (0, _localization2.default)("or"), " ", ' <a href="/user/create">', (0, _localization2.default)("register here"), "</a>.", "</div>", "<% } %>", "<form>", '<label for="copy-modal-title">', (0, _localization2.default)("Enter a title for the new history"), ":", "</label><br />",
            // TODO: could use required here and the form validators
            // NOTE: use unescaped here if escaped in the modal function below
            '<input id="copy-modal-title" class="form-control" style="width: 100%" value="<%= name %>" />', '<p class="invalid-title bg-danger" style="color: red; margin: 8px 0px 8px 0px; display: none">', (0, _localization2.default)("Please enter a valid history title"), "</p>",
            // if allowAll, add the option to copy deleted datasets, too
            "<% if( allowAll ){ %>", "<br />", "<p>", (0, _localization2.default)("Choose which datasets from the original history to include:"), "</p>",
            // copy non-deleted is the default
            '<input name="copy-what" type="radio" id="copy-non-deleted" value="copy-non-deleted" ', '<% if( copyWhat === "copy-non-deleted" ){ print( "checked" ); } %>/>', '<label for="copy-non-deleted"> <%- activeLabel %></label>', "<br />", '<input name="copy-what" type="radio" id="copy-all" value="copy-all" ', '<% if( copyWhat === "copy-all" ){ print( "checked" ); } %>/>', '<label for="copy-all"> <%- allLabel %></label>', "<% } %>", "</form>"
        ].join("")),

        // empty modal body and let the user know the copy is happening
        _showAjaxIndicator: function _showAjaxIndicator() {
            var indicator = "<p><span class=\"fa fa-spinner fa-spin\"></span> " + this.progressive + "...</p>";
            this.modal.$(".modal-body").empty().append(indicator).css({
                "margin-top": "8px"
            });
        },

        // (sorta) public interface - display the modal, render the form, and potentially copy the history
        // returns a jQuery.Deferred done->history copied, fail->user cancelled
        dialog: function _dialog(modal, history, options) {
            options = options || {};

            var dialog = this;
            var deferred = jQuery.Deferred();

            var // TODO: getting a little byzantine here
                defaultCopyNameFn = options.nameFn || this.defaultName;

            var defaultCopyName = defaultCopyNameFn({
                name: history.get("name")
            });

            var // TODO: these two might be simpler as one 3 state option (all,active,no-choice)
                defaultCopyWhat = options.allDatasets ? "copy-all" : "copy-non-deleted";

            var allowAll = !_.isUndefined(options.allowAll) ? options.allowAll : true;

            var autoClose = !_.isUndefined(options.autoClose) ? options.autoClose : true;

            this.modal = modal;

            // validate the name and copy if good
            function checkNameAndCopy() {
                var name = modal.$("#copy-modal-title").val();
                if (!name) {
                    modal.$(".invalid-title").show();
                    return;
                }
                // get further settings, shut down and indicate the ajax call, then hide and resolve/reject
                var copyAllDatasets = modal.$('input[name="copy-what"]:checked').val() === "copy-all";
                modal.$("button").prop("disabled", true);
                dialog._showAjaxIndicator();
                history.copy(true, name, copyAllDatasets).done(function(response) {
                    deferred.resolve(response);
                }).fail(function(xhr, status, message) {
                    var options = {
                        name: name,
                        copyAllDatasets: copyAllDatasets
                    };
                    _errorModal2.default.ajaxErrorModal(history, xhr, options, dialog.errorMessage);
                    deferred.rejectWith(deferred, arguments);
                }).done(function() {
                    if (autoClose) {
                        modal.hide();
                    }
                });
            }

            var originalClosingCallback = options.closing_callback;
            modal.show(_.extend(options, {
                title: this.title({
                    name: history.get("name")
                }),
                body: $(dialog._template({
                    name: defaultCopyName,
                    isAnon: Galaxy.user.isAnonymous(),
                    allowAll: allowAll,
                    copyWhat: defaultCopyWhat,
                    activeLabel: this.activeLabel,
                    allLabel: this.allLabel,
                    anonWarning: this.anonWarning
                })),
                buttons: _.object([
                    [(0, _localization2.default)("Cancel"), function() {
                        modal.hide();
                    }],
                    [this.submitLabel, checkNameAndCopy]
                ]),
                height: "auto",
                closing_events: true,
                closing_callback: function _historyCopyClose(cancelled) {
                    if (cancelled) {
                        deferred.reject({
                            cancelled: true
                        });
                    }
                    if (originalClosingCallback) {
                        originalClosingCallback(cancelled);
                    }
                }
            }));

            // set the default dataset copy, autofocus the title, and set up for a simple return
            modal.$("#copy-modal-title").focus().select();
            modal.$("#copy-modal-title").on("keydown", function(ev) {
                if (ev.keyCode === 13) {
                    ev.preventDefault();
                    checkNameAndCopy();
                }
            });

            return deferred;
        }
    };

    //==============================================================================
    // maintain the (slight) distinction between copy and import
    /**
     * Subclass CopyDialog to use the import language.
     */
    var ImportDialog = _.extend({}, CopyDialog, {
        defaultName: _.template("imported: <%- name %>"),
        title: _.template((0, _localization2.default)("Importing history") + " \"<%- name %>\""),
        submitLabel: (0, _localization2.default)("Import"),
        errorMessage: (0, _localization2.default)("History could not be imported."),
        progressive: (0, _localization2.default)("Importing history"),
        activeLabel: (0, _localization2.default)("Import only the active, non-deleted datasets"),
        allLabel: (0, _localization2.default)("Import all datasets including deleted ones"),
        anonWarning: (0, _localization2.default)("As an anonymous user, unless you login or register, you will lose your current history ") + (0, _localization2.default)("after importing this history. ")
    });

    //==============================================================================
    /**
     * Main interface for both history import and history copy dialogs.
     * @param  {Backbone.Model} history     the history to copy
     * @param  {Object}         options     a hash
     * @return {jQuery.Deferred}            promise that fails on close and succeeds on copy
     *
     * options:
     *     (this object is also passed to the modal used to display the dialog and accepts modal options)
     *     {Function} nameFn    if defined, use this to build the default name shown to the user
     *                          (the fn is passed: {name: <original history's name>})
     *     {bool} useImport     if true, use the 'import' language (instead of Copy)
     *     {bool} allowAll      if true, allow the user to choose between copying all datasets and
     *                          only non-deleted datasets
     *     {String} allDatasets default initial checked radio button: 'copy-all' or 'copy-non-deleted',
     */
    var historyCopyDialog = function historyCopyDialog(history, options) {
        options = options || {};
        // create our own modal if Galaxy doesn't have one (mako tab without use_panels)
        var modal = window.parent.Galaxy.modal || new _uiModal2.default.View({});
        return options.useImport ? ImportDialog.dialog(modal, history, options) : CopyDialog.dialog(modal, history, options);
    };

    //==============================================================================
    exports.default = historyCopyDialog;
});
//# sourceMappingURL=../../../maps/mvc/history/copy-dialog.js.map
