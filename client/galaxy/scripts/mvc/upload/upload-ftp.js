/** This renders the content of the ftp popup **/
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import UploadUtils from "mvc/upload/upload-utils";

export default Backbone.View.extend({
    initialize: function(options) {
        this.model = new Backbone.Model({
            cls: "upload-ftp",
            class_add: "upload-icon-button fa fa-square-o",
            class_remove: "upload-icon-button fa fa-check-square-o",
            class_partial: "upload-icon-button fa fa-minus-square-o",
            help_enabled: true,
            oidc_text: `<br/>If you are signed-in to Galaxy using a third-party identity and you <strong>don't have a Galaxy password</strong> please go to <a href="${getAppRoot()}user/reset_password" target="_blank">this</a> page and request a password for your Galaxy account.`,
            help_text: `This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>${
                options.ftp_upload_site
            }</strong> using your Galaxy credentials.
            For help visit the <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.`,
            collection: null,
            onchange: function() {},
            onadd: function() {},
            onremove: function() {}
        }).set(options);

        this.collection = this.model.get("collection");
        let Galaxy = getGalaxyInstance();
        if (Galaxy.config.enable_oidc) {
            this.model.set("help_text", this.model.get("help_text") + this.model.get("oidc_text"));
        }
        this.setElement(this._template());
        this.$content = this.$(".upload-ftp-content");
        this.$wait = this.$(".upload-ftp-wait");
        this.$help = this.$(".upload-ftp-help");
        this.$number = this.$(".upload-ftp-number");
        this.$disk = this.$(".upload-ftp-disk");
        this.$body = this.$(".upload-ftp-body");
        this.$warning = this.$(".upload-ftp-warning");
        this.$select = this.$(".upload-ftp-select-all");
        this.render();
    },

    render: function() {
        var self = this;
        this.$wait.show();
        this.$content.hide();
        this.$warning.hide();
        this.$help.hide();
        UploadUtils.getRemoteFiles(
            function(ftp_files) {
                self.model.set("ftp_files", ftp_files);
                self._index();
                self._renderTable();
            },
            function() {
                self._renderTable();
            }
        );
    },

    /** Fill table with ftp entries */
    _renderTable: function() {
        var self = this;
        var ftp_files = this.model.get("ftp_files");
        this.rows = [];
        if (ftp_files && ftp_files.length > 0) {
            this.$body.empty();
            var size = 0;
            _.each(ftp_files, ftp_file => {
                self.rows.push(self._renderRow(ftp_file));
                size += ftp_file.size;
            });
            this.$number.html(`${ftp_files.length} files`);
            this.$disk.html(Utils.bytesToString(size, true));
            if (this.collection) {
                this.$("._has_collection").show();
                this.$select
                    .addClass(this.model.get("class_add"))
                    .off()
                    .on("click", () => {
                        self._all();
                    });
                this._refresh();
            }
            this.$content.show();
        } else {
            this.$warning.show();
        }
        this.model.get("help_enabled") && this.$help.show();
        this.$wait.hide();
    },

    /** Add row */
    _renderRow: function(ftp_file) {
        var self = this;
        var options = this.model.attributes;
        var $it = $(this._templateRow(ftp_file));
        var $icon = $it.find(".icon");
        this.$body.append($it);
        if (this.collection) {
            var model_index = this.ftp_index[ftp_file.path];
            $icon.addClass(model_index === undefined ? options.class_add : options.class_remove);
            $it.on("click", () => {
                self._switch($icon, ftp_file);
                self._refresh();
            });
        } else {
            $it.on("click", () => {
                options.onchange(ftp_file);
            });
        }
        return $icon;
    },

    /** Create ftp index */
    _index: function() {
        var self = this;
        this.ftp_index = {};
        this.collection &&
            this.collection.each(model => {
                if (model.get("file_mode") == "ftp") {
                    self.ftp_index[model.get("file_path")] = model.id;
                }
            });
    },

    /** Select all event handler */
    _all: function() {
        var options = this.model.attributes;
        var ftp_files = this.model.get("ftp_files");
        var add = this.$select.hasClass(options.class_add);
        for (var index in ftp_files) {
            var ftp_file = ftp_files[index];
            var model_index = this.ftp_index[ftp_file.path];
            if ((model_index === undefined && add) || (model_index !== undefined && !add)) {
                this._switch(this.rows[index], ftp_file);
            }
        }
        this._refresh();
    },

    /** Handle collection changes */
    _switch: function($icon, ftp_file) {
        $icon.removeClass();
        var options = this.model.attributes;
        var model_index = this.ftp_index[ftp_file.path];
        if (model_index === undefined) {
            var new_index = options.onadd(ftp_file);
            $icon.addClass(options.class_remove);
            this.ftp_index[ftp_file.path] = new_index;
        } else {
            options.onremove(model_index);
            $icon.addClass(options.class_add);
            this.ftp_index[ftp_file.path] = undefined;
        }
    },

    /** Refresh select all button state */
    _refresh: function() {
        var counts = _.reduce(
            this.ftp_index,
            (memo, element) => {
                element !== undefined && memo++;
                return memo;
            },
            0
        );
        this.$select.removeClass();
        if (counts == 0) {
            this.$select.addClass(this.model.get("class_add"));
        } else {
            this.$select.addClass(
                counts == this.rows.length ? this.model.get("class_remove") : this.model.get("class_partial")
            );
        }
    },

    /** Template of row */
    _templateRow: function(options) {
        return `<tr class="upload-ftp-row">
                    <td class="_has_collection" style="display: none;">
                        <div class="icon"/>
                    </td>
                    <td class="ftp-name">${_.escape(options.path)}</td>
                    <td class="ftp-size">${Utils.bytesToString(options.size)}</td>
                    <td class="ftp-time">${options.ctime}</td>
                </tr>`;
    },

    /** Template of main view */
    _template: function() {
        return `<div class="${this.model.get("cls")}">
                    <div class="upload-ftp-wait fa fa-spinner fa-spin"/>
                    <div class="upload-ftp-help">${this.model.get("help_text")}</div>
                    <div class="upload-ftp-content">
                        <span style="whitespace: nowrap; float: left;">Available files: </span>
                        <span style="whitespace: nowrap; float: right;">
                            <span class="upload-icon fa fa-file-text-o"/>
                            <span class="upload-ftp-number"/>
                            <span class="upload-icon fa fa-hdd-o"/>
                            <span class="upload-ftp-disk"/>
                        </span>
                        <table class="grid" style="float: left;">
                            <thead>
                                <tr>
                                    <th class="_has_collection" style="display: none;">
                                        <div class="upload-ftp-select-all">
                                    </th>
                                    <th>Name</th>
                                    <th>Size</th>
                                    <th>Created</th>
                                </tr>
                            </thead>
                            <tbody class="upload-ftp-body"/>
                        </table>
                    </div>
                    <div class="upload-ftp-warning warningmessage">Your FTP directory does not contain any files.</div>
                </div>`;
    }
});
