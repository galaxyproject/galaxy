/** Renders the collection uploader rows */
import $ from "jquery";
import _ from "underscore";
import Utils from "utils/utils";
import UploadBoxRow from "mvc/upload/uploadbox-row";
export default UploadBoxRow.extend({
    initialize: function (app, options) {
        var self = this;
        this.app = app;
        this.model = options.model;
        this.setElement(this._template(options.model));
        this.$mode = this.$(".upload-mode");
        this.$title = this.$(".upload-title-extended");
        this.$text = this.$(".upload-text");
        this.$size = this.$(".upload-size");
        this.$info_text = this.$(".upload-info-text");
        this.$info_progress = this.$(".upload-info-progress");
        this.$text_content = this.$(".upload-text-content");
        this.$symbol = this.$(".upload-symbol");
        this.$progress_bar = this.$(".upload-progress-bar");
        this.$percentage = this.$(".upload-percentage");

        this._setupSettings();

        // handle click event
        this.$symbol.on("click", () => {
            self._removeRow();
        });

        // handle text editing event
        this.$text_content.on("change input", (e) => {
            self.model.set({
                url_paste: $(e.target).val(),
                file_size: $(e.target).val().length,
            });
        });

        // model events
        this._setupUploadBoxListeners();
        this.listenTo(this.model, "remove", () => {
            self.remove();
        });
        this.app.collection.on("reset", () => {
            self.remove();
        });
    },

    render: function () {
        var options = this.model.attributes;
        this.$title.html(_.escape(options.file_name));
        this.$size.html(Utils.bytesToString(options.file_size));
        this.$mode.removeClass().addClass("upload-mode").addClass("text-primary");
        if (options.file_mode == "new") {
            this.$text
                .css({
                    width: `${this.$el.width() - 16}px`,
                    top: `${this.$el.height() - 8}px`,
                })
                .show();
            this.$el.height(this.$el.height() - 8 + this.$text.height() + 16);
            this.$mode.addClass("fa fa-edit");
        } else if (options.file_mode == "local") {
            this.$mode.addClass("fa fa-laptop");
        } else if (options.file_mode == "ftp") {
            this.$mode.addClass("fa fa-folder-open-o");
        }
    },

    /** Refresh status */
    _refreshStatus: function () {
        var status = this.model.get("status");
        this.$symbol.removeClass().addClass("upload-symbol").addClass(this.status_classes[status]);
        this.model.set("enabled", status == "init");
        var enabled = this.model.get("enabled");
        this.$text_content.attr("disabled", !enabled);
        this._renderStatusType(status);
    },

    /** View template */
    _template: function (options) {
        return `<tr id="upload-row-${options.id}" class="upload-row"><td><div class="upload-text-column"><div class="upload-mode"/><div class="upload-title-extended"/><div class="upload-text"><div class="upload-text-info">Download data from the web by entering URLs (one per line) or directly paste content.</div><textarea class="upload-text-content form-control"/></div></div></td><td><div class="upload-size"/></td><td><div class="upload-info"><div class="upload-info-text"/><div class="upload-info-progress progress"><div class="upload-progress-bar progress-bar progress-bar-success"/><div class="upload-percentage">0%</div></div></div></td><td><div class="upload-symbol ${this.status_classes.init}"/></td></tr>`;
    },
});
