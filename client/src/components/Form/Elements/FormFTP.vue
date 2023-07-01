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
            <b-table
                id="ftp-table"
                class="grid"
                hover
                no-sort-reset
                no-local-sorting
                :items="filesSource"
                :fields="fields"
                @row-clicked="onRowClicked">
                <template v-slot:head(check)>
                    <b-checkbox
                        id="upload-ftp-select-all"
                        class="upload-ftp-select-all"
                        :ftp-id="'*'"
                        @click="selectAll"></b-checkbox>
                </template>
                <template v-slot:cell(check)="{ item }">
                    <div>
                        <b-checkbox v-model="item.check"></b-checkbox>
                    </div>
                </template>
                <template v-slot:cell(name)="data">
                    {{ escape(data.item.name) }}
                </template>
                <template v-slot:cell(size)="data">
                    {{ bytesToString(data.item.size) }}
                </template>
                <template v-slot:cell(ctime)="data">
                    {{ data.item.ctime }}
                </template>
            </b-table>
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
            fields: [
                { key: "check" },
                {
                    key: "Name",
                    sortable: false,
                },
                {
                    key: "Size",
                    sortable: false,
                },
                {
                    key: "Ctime",
                    label: "Created",
                    sortable: false,
                },
            ],
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
                Object.values(this.filesSource).forEach((element) => {
                    // element["check"] = false;
                });
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
                files.forEach((file) => {
                    self.rows.push(file);
                    size += file.size;
                });
                this.totalSize = size;
            } else {
                this.$nextTick(() => {
                    this.$el.querySelector(".upload-ftp-warning").style.display = "block";
                });
            }
            this.waiting = false;
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
            var add = this.$el
                .getElementsByClassName("upload-ftp-select-all")[0]
                .classList.value.includes(this.model.checkbox.add);
            for (var f in files) {
                var file = files[f];
                var index = this.filesTarget[file.path];
                if ((index === undefined && add) || (index !== undefined && !add)) {
                    this._updateCheckboxes(this._templateRow(file.path).getElementsByClassName("icon")[0], file);
                }
            }
        },
        onRowClicked(item, index) {
            this.toggleDetails(item, index);
            this._updateCheckboxes(item);
        },
        toggleDetails(item, index) {
            // item.check = !item.check;
            this.filesSource[index].check = !this.filesSource[index].check;
        },
        _templateRow: function (rowId) {
            return this.$el.querySelector(`[ftp-id="${rowId}"]`);
        },
        _updateCheckboxes: function (file) {
            var index = this.filesTarget[file.path];
            if (index === undefined) {
                var indexNew = this.model.onadd(this.model.upload_box, file);
                this.filesTarget[file.path] = indexNew;
            } else {
                this.model.onremove(this.model.collection, index);
                delete this.filesTarget[file.path];
            }
        },
        isSelected: function (file) {
            return this.filesTarget[file.path] !== undefined;
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
