<template>
    <div :class="model.attributes.cls" id="upload-ftp">
    {{ /* //TODO model.cls = "upload-ftp" */ }}
        <div v-show="waiting" class="upload-ftp-wait fa fa-spinner fa-spin" />
        <div v-show="model.help_enabled" class="upload-ftp-help">
            This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>{{ this.model.ftp_upload_site }}</strong> using your Galaxy credentials. For help visit the <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
            <span v-show="model.oidc_text">
                <br/>If you are signed-in to Galaxy using a third-party identity and you <strong>do not have a Galaxy password</strong> please use the reset password option in the login form with your email to create a password for your account.
            </span>
        </div>
        <div v-show="!waiting" class="upload-ftp-content">
            <span style="whitespace: nowrap; float: left">Available files: </span>
            <span style="whitespace: nowrap; float: right">
                <span class="upload-icon fa fa-file-text-o" />
                <span class="upload-ftp-number">{{ ftpFiles.length }} files</span>
                <span class="upload-icon fa fa-hdd-o" />
                <span class="upload-ftp-disk">{{ bytesToString(totalSize, true) }}</span>
            </span>
            <table class="grid" style="float: left">
                <thead>
                    <tr>
                        <th v-show="model.collection" class="_has_collection">
                            <div
                                class="upload-ftp-select-all"
                                :class="{ [model.attributes.class_add]: !isAllSelected, [model.attributes.class_remove]: isAllSelected }"
                                @click="selectAll"></div>
                        </th>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody class="upload-ftp-body">
                    <tr
                        v-for="(ftpFile, index) in ftpFiles"
                        :key="ftpFile.path"
                        :ftp-id="ftpFile.path"
                        class="upload-ftp-row"
                        @click="onRowClick(ftpFile)">
                        <td class="_has_collection">
                            <div
                                class="icon"
                                :class="{
                                    [model.attributes.class_add]: !isSelected(ftpFile),
                                    [model.attributes.class_remove]: isSelected(ftpFile),
                                }"></div>
                        </td>
                        <td class="ftp-name">
                            {{ escape(ftpFile.path) }}
                        </td>
                        <td class="ftp-size">{{ bytesToString(ftpFile.size) }}</td>
                        <td class="ftp-time">{{ ftpFile.ctime }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-show="ftpFiles.length === 0" class="upload-ftp-warning warningmessage">no files.</div>
    </div>
</template>

<script>
import _ from "underscore";
import $ from "jquery"; //TODO remove
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import UploadUtils from "mvc/upload/upload-utils";

export default {
    props: ["options", "collection"],
    data() {
        return {
            model: {
                attributes: {
                    cls: "upload-ftp", //TODO cls: "FormFTP",
                    class_add: "upload-icon-button fa fa-square-o",
                    class_remove: "upload-icon-button fa fa-check-square-o",
                    class_partial: "upload-icon-button fa fa-minus-square-o",
                },
                help_enabled: true,
                oidc_text: false,
                collection: null,
            },
            ftpFiles: [],
            waiting: true,
            totalSize: 0,
            isAllSelected: false,
            ftpIndex: {},
        };
    },
    created() {
        this.model = _.extend(this.model, this.options);
        this.model.collection = this.collection;
        const Galaxy = getGalaxyInstance();
        if (Galaxy.config.enable_oidc) {
            this.model.oidc_text = true;
        }
    },
    mounted() {
        UploadUtils.getRemoteFiles(
            (ftp_files) => {
                this.ftpFiles = ftp_files;
                this._index();
                this._renderTable();
            },
            () => {
                this._renderTable();
            }
        );
    },
    methods: {
        /** Fill table with ftp entries */
        _renderTable: function () {
            var ftp_files = this.ftpFiles;
            this.rows = [];
            if (ftp_files && ftp_files.length > 0) {
                this.$nextTick(() => {
                    this.$el.querySelector(".upload-ftp-content").style.display = "block";
                    this.$el.querySelector(".upload-ftp-warning").style.display = "none";
                });
                var size = 0;
                _.each(ftp_files, (ftp_file) => {
                    this.rows.push(ftp_file);
                    size += ftp_file.size;
                });
                this.totalSize = size;
                if (this.collection) {
                    this.$nextTick(() => {
                        this.$el.querySelector("._has_collection").style.display = "table-cell";
                    });
                }
            } else {
                this.$nextTick(() => {
                    this.$el.querySelector(".upload-ftp-warning").style.display = "block";
                });
            }
            this.waiting = false;
        },

        /** Add row */
        _renderRow: function (ftp_file) {
            var self = this;
            var options = this.model.attributes;
            var $it = $(this._templateRow(ftp_file));
            var $icon = $it.find(".icon");
            this.$body.append($it);
            if (this.collection) {
                var model_index = this.ftpIndex[ftp_file.path];
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
        _index: function () {
            this.ftpIndex = {};
            if (this.collection) {
                this.collection.each((model) => {
                    if (model.get("file_mode") == "ftp") {
                        this.ftpIndex[model.get("file_path")] = model.id;
                    }
                });
            }
        },

        /** Select all event handler */
        selectAll: function () {
            var ftp_files = this.ftpFiles;
            var $it = $(this._templateRow(ftp_file));
            var $icon = $it.find(".icon");
            var add = this.$el.querySelector(".upload-ftp-select-all").classList.contains(this.model.attributes.class_add);
            for (var index in ftp_files) {
                var ftp_file = ftp_files[index];
                var model_index = this.ftpIndex[ftp_file.path];
                if ((model_index === undefined && add) || (model_index !== undefined && !add)) {
                    this._switch($icon, ftp_file);
                }
            }
            this.isAllSelected = !this.isAllSelected;
            this._refresh();
        },

        /** Handle row click */
        onRowClick: function (ftp_file) {
            var self = this;
            var $it = $(this._templateRow(ftp_file)); //TODO needs to be replaced
            var $icon = $it.find(".icon");
            if (this.collection) {
                this._switch($icon, ftp_file);
            } else {
                this.model.onchange(ftp_file);
            }
            self._refresh();
        },

        /** Template of row */
        _templateRow: function (options) {
            return $(`[ftp-id="${options.path}"]`);
        },

        /** Handle collection changes */
        _switch: function ($icon, ftp_file) {
            var options = this.model.attributes;
            $icon.removeClass();
            var model_index = this.ftpIndex[ftp_file.path];
            if (model_index === undefined) {
                var new_index = this.model.onadd(this.model.upload_box, ftp_file);
                $icon.addClass(options.class_remove); //TODO replace this jQuery for the check/uncheck box with Vue.js
                this.ftpIndex[ftp_file.path] = new_index;
            } else {
                this.model.onremove(this.model.collection, model_index);
                $icon.addClass(options.class_add);
                delete this.ftpIndex[ftp_file.path];
            }
        },

        /** Refresh select all button state */
        _refresh: function () {
            var counts = _.reduce(
                this.ftpIndex,
                (memo, element) => {
                    element !== undefined && memo++;
                    return memo;
                },
                0
            );
            $(".upload-ftp-select-all").removeClass();
            if (counts == 0) {
                $(".upload-ftp-select-all").addClass(options.class_add);
            } else {
                $(".upload-ftp-select-all").addClass(
                    counts == this.rows.length ? options.class_remove : options.class_partial
                );
            }
        },

        /** Check if file is selected */
        isSelected: function (ftp_file) {
            return this.ftpIndex[ftp_file.path] !== undefined;
        },

        /** Convert bytes to string */
        bytesToString: function (bytes, si) {
            return Utils.bytesToString(bytes, si);
        },
        escape(filepath) {
            return _.escape(filepath);
        },
    },
};
</script>
