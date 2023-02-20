<template>
    <div :class="model.cls">
        <div class="upload-ftp-wait fa fa-spinner fa-spin" v-show="waiting"/>
        <div class="upload-ftp-help" v-show="model.help_enabled">{{ model.help_text }}</div>
        <div class="upload-ftp-content" v-show="!waiting">
            <span style="whitespace: nowrap; float: left;">Available files: </span>
            <span style="whitespace: nowrap; float: right;">
                <span class="upload-icon fa fa-file-text-o"/>
                <span class="upload-ftp-number">{{ ftpFiles.length }} files</span>
                <span class="upload-icon fa fa-hdd-o"/>
                <span class="upload-ftp-disk">{{ bytesToString(totalSize, true) }}</span>
            </span>
            <table class="grid" style="float: left;">
                <thead>
                    <tr>
                        <th class="_has_collection" v-show="model.collection">
                            <div class="upload-ftp-select-all" :class="{[model.class_add]: !isAllSelected, [model.class_remove]: isAllSelected}" @click="selectAll">
                            </div>
                        </th>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody class="upload-ftp-body">
                    <tr class="upload-ftp-row" v-for="(ftpFile, index) in ftpFiles" :key="ftpFile.path" @click="onRowClick(ftpFile)">
                        <td class="ftp-name" colspan="4">
                            <div class="icon" :class="{[model.class_add]: !isSelected(ftpFile), [model.class_remove]: isSelected(ftpFile)}"></div>
                            {{ ftpFile.path }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="upload-ftp-warning warningmessage" v-show="ftpFiles.length === 0">no files.</div>
    </div>
</template>
  
<script>
import _ from "underscore";
import $ from "jquery";
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import UploadUtils from "mvc/upload/upload-utils";
  
  export default { //TODO <----- realign margins
    props: ["options"],
    data() {
      return {
        model: {
          cls: "upload-ftp",
          class_add: "class_add",
          class_remove: "class_remove",
          class_partial: "class_partial",
          help_enabled: true,
          oidc_text: `<br/>If you are signed-in to Galaxy using a third-party identity and you <strong>do not have a Galaxy password</strong> please use the reset password option in the login form with your email to create a password for your account.`,
          help_text: `This Galaxy server allows you to upload files via FTP. To upload some files, log in to the FTP server at <strong>${options.ftp_upload_site}</strong> using your Galaxy credentials. For help visit the <a href="https://galaxyproject.org/ftp-upload/" target="_blank">tutorial</a>.`,
          collection: null,
          onchange: () => {},
          onadd: () => {},
          onremove: () => {},
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
      this.collection = this.model.collection;
      const Galaxy = getGalaxyInstance();
      if (Galaxy.config.enable_oidc) {
        this.model.help_text = this.model.help_text + this.model.oidc_text;
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
        return this.ftpIndex[ftp_file.path];
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
        var add = this.$el.querySelector(".upload-ftp-select-all").classList.contains(this.model.class_add);
        for (var index in ftp_files) {
          var ftp_file = ftp_files[index];
          var model_index = this.ftpIndex[ftp_file.path];
          if ((model_index === undefined && add) || (model_index !== undefined && !add)) {
            this._switch(ftp_file);
          }
        }
        this.isAllSelected = !this.isAllSelected;
      },
    
      /** Handle row click */
      onRowClick: function (ftp_file) {
        if (this.collection) {
          this._switch(ftp_file);
        } else {
          this.model.onchange(ftp_file);
        }
      },
    
      /** Handle collection changes */
      _switch: function (ftp_file) {
        var icon = this.ftpIndex[ftp_file.path];
        if (icon === undefined) {
          var new_index = this.model.onadd(ftp_file);
          this.$set(this.ftpIndex, ftp_file.path, new_index);
        } else {
          this.model.onremove(icon);
          this.$delete(this.ftpIndex, ftp_file.path);
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
    },
};
</script>
  