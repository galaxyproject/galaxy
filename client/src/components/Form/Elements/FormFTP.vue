<template>
    <div :class="model.class">
        <div v-show="waiting" class="upload-ftp-wait fa fa-spinner fa-spin" />
        <div v-show="model.text.help" class="upload-ftp-help">
            This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at
            <strong>{{ model.ftp_upload_site }}</strong> using your Galaxy credentials. For help visit the
            <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.
            <span v-show="model.text.oidc">
                <br />If you are signed-in to Galaxy using a third-party identity and you
                <strong>do not have a Galaxy password</strong> please use the reset password option in the login form
                with your email to create a password for your account.
            </span>
        </div>
        <div v-show="!waiting" class="upload-ftp-content">
            <span style="whitespace: nowrap; float: left">Available files: </span>
            <span style="whitespace: nowrap; float: right">
                <span class="upload-icon fa fa-file-text-o" />
                <span class="upload-ftp-number">{{ filesSource.length }} files</span>
                <span class="upload-icon fa fa-hdd-o" />
                <span class="upload-ftp-disk">{{ bytesToString(totalSize, true) }}</span>
            </span>
            <table class="grid" style="float: left">
                <thead>
                    <tr>
                        <th v-show="model.collection" class="_has_collection">
                            <div
                                class="upload-ftp-select-all"
                                id="upload-ftp-select-all"
                                :ftp-id="'*'"
                                :class="selectAllStatus"
                                @click="selectAll"></div>
                        </th>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody class="upload-ftp-body">
                    <tr
                        v-for="(file, index) in filesSource"
                        :key="file.path"
                        :ftp-id="file.path"
                        :ftp-index="index"
                        class="upload-ftp-row"
                        @click="onRowClick(file)">
                        <td class="_has_collection">
                            <div
                                class="icon"
                                :class="{
                                    [model.checkbox.add]: !isSelected(file),
                                    [model.checkbox.remove]: isSelected(file),
                                }"></div>
                        </td>
                        <td class="ftp-name">
                            {{ escape(file.path) }}
                        </td>
                        <td class="ftp-size">{{ bytesToString(file.size) }}</td>
                        <td class="ftp-time">{{ file.ctime }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-show="filesSource.length === 0" class="upload-ftp-warning warningmessage">no files.</div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import UploadUtils from "mvc/upload/upload-utils";

export default {
    props: ["options", "collection"],
    data() {
        return {
            model: {
                class: "upload-ftp",
                checkbox: {
                    add: "upload-icon-button fa fa-square-o",
                    remove: "upload-icon-button fa fa-check-square-o",
                    partial: "upload-icon-button fa fa-minus-square-o",
                },
                text: {
                    help: true,
                    oidc: false,
                },
                collection: null,
            },
            filesSource: [],
            filesTarget: {},
            totalSize: 0,
            waiting: true,
        };
    },
    computed: {
        selectAllStatus() {
            var status = this.model.checkbox.add;
            if (Object.keys(this.filesTarget).length > 0) {
                status =
                    this.filesSource.length === Object.keys(this.filesTarget).length
                        ? this.model.checkbox.remove
                        : this.model.checkbox.partial;
            }

            return status;
        },
    },
    created() {
        this.model = Object.assign(this.model, this.options);
        this.model.collection = this.collection;
        const Galaxy = getGalaxyInstance();
        if (Galaxy.config.enable_oidc) {
            this.model.text.oidc = true;
        }
    },
    mounted() {
        UploadUtils.getRemoteFiles(
            (files) => {
                this.filesSource = files;
                this._buildFtpIndex();
                this._renderTable();
            },
            () => {
                this._renderTable();
            }
        );
    },
    methods: {
        _renderTable: function () {
            var self = this;
            var files = this.filesSource;
            this.rows = [];
            if (files && files.length > 0) {
                this.$nextTick(() => {
                    this.$el.querySelector(".upload-ftp-content").style.display = "block";
                    this.$el.querySelector(".upload-ftp-warning").style.display = "none";
                });
                var size = 0;
                files.forEach(file => {
                    self.rows.push(file);
                    size += file.size;
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
        _renderRow: function (file) {
            var self = this;
            var options = this.model.checkbox;
            var it = this._templateRow(file.path);
            var icon = it.getElementsByClassName("icon")[0];
            this.$body.append(it);
            if (this.collection) {
                var index = this.filesTarget[file.path];
                icon.classList.add(...(index === undefined ? options.add : options.remove).split(' '));
                it.addEventListener("click", () => {
                    self._updateCheckboxes(icon, file);
                    self._refreshCheckboxes();
                });
            } else {
                it.addEventListener("click", () => {
                    options.onchange(file);
                });
            }
            return icon;
        },
        _buildFtpIndex: function () {
            this.filesTarget = {};
            if (this.collection) {
                this.collection.each((model) => {
                    if (model.get("file_mode") == "ftp") {
                        this.filesTarget[model.get("file_path")] = model.id;
                    }
                });
            }
        },
        selectAll: function () {
            var files = this.filesSource;
            var add = (this.$el.getElementsByClassName('upload-ftp-select-all')[0].classList.value).includes(this.model.checkbox.add);
            for (var f in files) {
                var file = files[f];
                var index = this.filesTarget[file.path];
                if ((index === undefined && add) || (index !== undefined && !add)) {
                    this._updateCheckboxes(this._templateRow(file.path).getElementsByClassName("icon")[0], file);
                }
            }
            this._refreshCheckboxes();
        },
        onRowClick: function (file) {
            var self = this;
            var it = (this._templateRow(file.path));
            var icon = it.getElementsByClassName("icon")[0];
            if (this.collection) {
                this._updateCheckboxes(icon, file);
            } else {
                this.model.onchange(file);
            }
            self._refreshCheckboxes();
        },
        _templateRow: function (rowId) {
            return this.$el.querySelector(`[ftp-id="${rowId}"]`);
        },
        _updateCheckboxes: function (icon, file) {
            var options = this.model.checkbox;
            icon.classList.remove(...options.add.split(' '));
            var index = this.filesTarget[file.path];
            if (index === undefined) {
                var indexNew = this.model.onadd(this.model.upload_box, file);
                icon.classList.add(...options.remove.split(' '));
                this.filesTarget[file.path] = indexNew;
            } else {
                this.model.onremove(this.model.collection, index);
                icon.classList.add(...options.add.split(' '));
                delete this.filesTarget[file.path];
            }
        },
        _refreshCheckboxes: function () {
            var counts = Object.keys(this.filesTarget).length;
            this.clearCheckbox("upload-ftp-select-all");
            if (counts === 0) {
                this.$el.getElementsByClassName('upload-ftp-select-all')[0].classList.add(...this.model.checkbox.add.split(' '));
            } else {
                this.$el.getElementsByClassName('upload-ftp-select-all')[0].classList.add(...(counts == this.rows.length ? this.model.checkbox.remove : this.model.checkbox.partial).split(' '));
            }
        },
        isSelected: function (file) {
            return this.filesTarget[file.path] !== undefined;
        },
        clearCheckbox(strClass) {
            this.$el.getElementsByClassName(strClass)[0].classList.remove(...this.model.checkbox.add.split(' '));
            this.$el.getElementsByClassName(strClass)[0].classList.remove(...this.model.checkbox.remove.split(' '));
            this.$el.getElementsByClassName(strClass)[0].classList.remove(...this.model.checkbox.partial.split(' '));
        },
        bytesToString: function (bytes, si) {
            return Utils.bytesToString(bytes, si);
        },
        escape(filepath) {
            return encodeURI(filepath);
        },
    },
};
</script>
