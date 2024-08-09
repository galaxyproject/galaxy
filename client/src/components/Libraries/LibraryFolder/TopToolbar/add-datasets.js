import "libs/jquery/jstree";

import { getGalaxyInstance } from "app";
import Backbone from "backbone";
import { Toast } from "composables/toast";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import _ from "underscore";
import _l from "utils/localization";

import { updateProgress } from "./delete-selected";
import mod_library_model from "./library-model";
import mod_select from "./ui-select";

var AddDatasets = Backbone.View.extend({
    options: null,

    initialize: function (options) {
        this.options = options;
        this.options.chain_call_control = {
            total_number: 0,
            failed_number: 0,
        };

        this.list_extensions = options.list_extensions;
        this.list_genomes = options.list_genomes;
        this.showImportModal(options);
    },

    /*
     Slightly adopted Backbone code
     */
    showImportModal: function (options) {
        switch (options.source) {
            case "importdir":
                this.importFilesFromGalaxyFolderModal({
                    source: "importdir",
                });
                break;
            case "path":
                this.importFilesFromPathModal();
                break;
            case "userdir":
                this.importFilesFromGalaxyFolderModal({
                    source: "userdir",
                });
                break;
            default:
                // Galaxy.libraries.library_router.back();
                Toast.error("Invalid import source.");
                break;
        }
    },
    templateBrowserModal: function () {
        return _.template(
            `<div id="file_browser_modal">
                    <div style="margin-bottom:1em;">
                        <label title="Switch to selecting files" class="radio-inline import-type-switch">
                            <input type="radio" name="jstree-radio" value="jstree-disable-folders" checked="checked">
                            Choose Files
                        </label>
                        <label title="Switch to selecting folders" class="radio-inline import-type-switch">
                            <input type="radio" name="jstree-radio" value="jstree-disable-files">
                            Choose Folders
                        </label>
                    </div>
                    <div class="alert alert-info jstree-files-message">
                        All files you select will be imported into the current folder ignoring their folder structure.
                    </div>
                    <div class="alert alert-info jstree-folders-message" style="display:none;">
                        All files within the selected folders and their subfolders will be imported into the current folder.
                    </div>
                    <div style="margin-bottom:1em;">
                        <label class="checkbox-inline jstree-preserve-structure" style="display:none;">
                            <input class="preserve-checkbox" type="checkbox" value="preserve_directory_structure">
                                Preserve directory structure
                            </label>
                        <label class="checkbox-inline">
                            <input class="link-checkbox" type="checkbox" value="link_files">
                                Link files instead of copying
                        </label>
                        <label class="checkbox-inline">
                            <input class="posix-checkbox" type="checkbox" value="to_posix_lines" checked="checked">
                                Convert line endings to POSIX
                        </label>
                        <label class="checkbox-inline">
                            <input class="spacetab-checkbox" type="checkbox" value="space_to_tab">
                                Convert spaces to tabs
                        </label>
                    </div>
                    <button title="Select all files" type="button" class="button primary-button libimport-select-all">
                        Select all
                    </button>
                    <button title="Select no files" type="button" class="button primary-button libimport-select-none">
                        Unselect all
                    </button>
                    <hr /> <!-- append jstree object here -->
                    <div id="jstree_browser">
                    </div>
                    <hr />
                    <p>You can set extension type and genome for all imported datasets at once:</p>
                    <div>
                        Type: <span id="library_extension_select" class="library-extension-select" />
                        Genome: <span id="library_genome_select" class="library-genome-select" />
                    </div>
                    <br />
                    <div>
                        <label class="checkbox-inline tag-files">
                            Tag datasets based on file names
                            <input class="tag-files" type="checkbox" value="tag_using_filenames">
                        </label>
                    </div>
                </div>`
        );
    },
    templateImportPathModal: function () {
        return _.template(
            `<div id="file_browser_modal">
                <div class="alert alert-info jstree-folders-message">
                    All files within the given folders and their subfolders will be imported into the current folder.
                </div>
                <div style="margin-bottom: 0.5em;">
                    <label class="checkbox-inline">
                        <input class="preserve-checkbox" type="checkbox" value="preserve_directory_structure">
                        Preserve directory structure
                    </label>
                    <label class="checkbox-inline">
                        <input class="link-checkbox" type="checkbox" value="link_files">
                        Link files instead of copying
                    </label>
                    <br>
                    <label class="checkbox-inline">
                        <input class="posix-checkbox" type="checkbox" value="to_posix_lines" checked="checked">
                        Convert line endings to POSIX
                    </label>
                    <label class="checkbox-inline">
                        <input class="spacetab-checkbox" type="checkbox" value="space_to_tab">
                        Convert spaces to tabs
                    </label>
                </div>
                <textarea id="import_paths" class="form-control" rows="5"
                    placeholder="Absolute paths (or paths relative to Galaxy root) separated by newline" autofocus>
                </textarea>
                <hr />
                <p>You can set extension type and genome for all imported datasets at once:</p>
                <div>
                    Type: <span id="library_extension_select" class="library-extension-select"></span>
                    Genome: <span id="library_genome_select" class="library-genome-select"></span>
                </div>
                <div>
                    <label class="checkbox-inline tag-files">
                        Tag datasets based on file names
                        <input class="tag-files" type="checkbox" value="tag_using_filenames">
                    </label>
                </div>
            </div>`
        );
    },
    renderSelectBoxes: function () {
        const Galaxy = getGalaxyInstance();
        // This won't work properly unlesss we already have the data fetched.
        // See this.fetchExtAndGenomes()
        this.select_genome = new mod_select.View({
            css: "library-genome-select",
            data: this.list_genomes,
            container: Galaxy.modal.$el.find("#library_genome_select"),
            value: "?",
        });
        this.select_extension = new mod_select.View({
            css: "library-extension-select",
            data: this.list_extensions,
            container: Galaxy.modal.$el.find("#library_extension_select"),
            value: "auto",
        });
    },
    /**
     * Create modal for importing from given directory
     * on Galaxy. Bind jQuery events.
     */
    importFilesFromGalaxyFolderModal: function (options) {
        var template_modal = this.templateBrowserModal();
        const Galaxy = getGalaxyInstance();
        this.modal = Galaxy.modal;
        this.modal.show({
            closing_events: true,
            title: _l("Please select folders or files"),
            body: template_modal({}),
            buttons: {
                Import: () => {
                    this.importFromJstreePath(this, options);
                },
                Close: () => {
                    Galaxy.modal.hide();
                },
            },
            closing_callback: () => {
                // TODO update table without fetching new content from the server
                this.options.updateContent();
                // Galaxy.libraries.library_router.navigate(`folders/${this.id}`, {
                //     trigger: true,
                // });
            },
        });

        $(".libimport-select-all").bind("click", () => {
            $("#jstree_browser").jstree("check_all");
        });
        $(".libimport-select-none").bind("click", () => {
            $("#jstree_browser").jstree("uncheck_all");
        });

        this.renderSelectBoxes();
        options.disabled_jstree_element = "folders";
        this.renderJstree(options);

        $("input[type=radio]").change((event) => {
            if (event.target.value === "jstree-disable-folders") {
                options.disabled_jstree_element = "folders";
                this.renderJstree(options);
                $(".jstree-folders-message").hide();
                $(".jstree-preserve-structure").hide();
                $(".jstree-files-message").show();
            } else if (event.target.value === "jstree-disable-files") {
                $(".jstree-files-message").hide();
                $(".jstree-folders-message").show();
                $(".jstree-preserve-structure").show();
                options.disabled_jstree_element = "files";
                this.renderJstree(options);
            }
        });
    },
    /**
     * Take the selected items from the jstree, create a request queue
     * and send them one by one to the server for importing into
     * the current folder.
     *
     * jstree.js has to be loaded before
     * @see renderJstree
     */
    importFromJstreePath: function (that, options) {
        var all_nodes = $("#jstree_browser").jstree().get_selected(true);
        // remove the disabled elements that could have been trigerred with the 'select all'
        var selected_nodes = _.filter(all_nodes, (node) => node.state.disabled == false);
        var preserve_dirs = this.modal.$el.find(".preserve-checkbox").is(":checked");
        var link_data = this.modal.$el.find(".link-checkbox").is(":checked");
        var space_to_tab = this.modal.$el.find(".spacetab-checkbox").is(":checked");
        var to_posix_lines = this.modal.$el.find(".posix-checkbox").is(":checked");
        var file_type = this.select_extension.value();
        var dbkey = this.select_genome.value();
        var tag_using_filenames = this.modal.$el.find(".tag-files").is(":checked");
        var selection_type = selected_nodes[0].type;
        var paths = [];
        if (selected_nodes.length < 1) {
            Toast.info("Please select some items first.");
        } else {
            this.modal.disableButton("Import");
            for (let i = selected_nodes.length - 1; i >= 0; i--) {
                if (selected_nodes[i].li_attr.full_path !== undefined) {
                    // should be always String
                    paths.push(`"${selected_nodes[i].li_attr.full_path}"`);
                }
            }
            this.initChainCallControlAddingDatasets({
                length: paths.length,
            });
            if (selection_type === "folder") {
                const full_source = `${options.source}_folder`;
                this.chainCallImportingFolders({
                    paths: paths,
                    preserve_dirs: preserve_dirs,
                    link_data: link_data,
                    space_to_tab: space_to_tab,
                    to_posix_lines: to_posix_lines,
                    source: full_source,
                    file_type: file_type,
                    dbkey: dbkey,
                    tag_using_filenames: tag_using_filenames,
                });
            } else if (selection_type === "file") {
                const full_source = `${options.source}_file`;
                this.chainCallImportingUserdirFiles({
                    paths: paths,
                    file_type: file_type,
                    dbkey: dbkey,
                    link_data: link_data,
                    space_to_tab: space_to_tab,
                    to_posix_lines: to_posix_lines,
                    source: full_source,
                    tag_using_filenames: tag_using_filenames,
                });
            }
        }
    },
    /**
     * Take the array of paths and create a request for each of them
     * calling them in chain. Update the progress bar in between each.
     * @param  {array} paths                    paths relative to user folder on Galaxy
     * @param  {boolean} tag_using_filenames    add tags to datasets using names of files
     */
    chainCallImportingUserdirFiles: function (options) {
        const Galaxy = getGalaxyInstance();
        const popped_item = options.paths.pop();
        if (typeof popped_item === "undefined") {
            if (this.options.chain_call_control.failed_number === 0) {
                Toast.success("Selected files imported into the current folder");
                Galaxy.modal.hide();
            } else {
                Toast.error("An error occurred.");
            }
            return true;
        }
        const post_url = `${getAppRoot()}api/libraries/datasets`;
        const post_data = {
            encoded_folder_id: this.id,
            source: options.source,
            path: popped_item,
            file_type: options.file_type,
            link_data: options.link_data,
            space_to_tab: options.space_to_tab,
            to_posix_lines: options.to_posix_lines,
            dbkey: options.dbkey,
            tag_using_filenames: options.tag_using_filenames,
        };
        const promise = $.when($.post(post_url, post_data));
        promise
            .done((response) => {
                updateProgress();
                this.chainCallImportingUserdirFiles(options);
            })
            .fail(() => {
                this.options.chain_call_control.failed_number += 1;
                updateProgress();
                this.chainCallImportingUserdirFiles(options);
            });
    },
    /**
     * Fetch the contents of user directory on Galaxy
     * and render jstree component based on received
     * data.
     * @param  {[type]} options [description]
     */
    renderJstree: function (options) {
        this.options = _.extend(this.options, options);
        var target = options.source || "userdir";
        var disabled_jstree_element = this.options.disabled_jstree_element;
        this.jstree = new mod_library_model.Jstree();
        this.jstree.url = `${this.jstree.urlRoot}?target=${target}&format=jstree&disable=${disabled_jstree_element}`;
        this.jstree.fetch({
            success: (model, response) => {
                $("#jstree_browser").jstree("destroy");
                $("#jstree_browser").jstree({
                    core: {
                        data: model,
                    },
                    plugins: ["types", "checkbox"],
                    types: {
                        folder: {
                            icon: "jstree-folder",
                        },
                        file: {
                            icon: "jstree-file",
                        },
                    },
                    checkbox: {
                        three_state: false,
                    },
                });
            },
            error: (model, response) => {
                if (typeof response.responseJSON !== "undefined") {
                    if (response.responseJSON.err_code === 404001) {
                        Toast.warning(response.responseJSON.err_msg);
                        getGalaxyInstance().modal.hide();
                    } else {
                        Toast.error(response.responseJSON.err_msg);
                    }
                } else {
                    Toast.error("An error occurred.");
                }
            },
        });
    },
    /**
     * Create modal for importing from Galaxy path.
     */
    importFilesFromPathModal: function () {
        const Galaxy = getGalaxyInstance();
        this.modal = Galaxy.modal;
        var template_modal = this.templateImportPathModal();
        this.modal.show({
            closing_events: true,
            title: _l("Please enter paths to import"),
            body: template_modal({}),
            buttons: {
                Import: () => {
                    this.importFromPathsClicked(this);
                },
                Close: () => {
                    Galaxy.modal.hide();
                },
            },
            closing_callback: () => {
                // TODO update table without fetching new content from the server
                this.options.updateContent();

                // Galaxy.libraries.library_router.navigate(`folders/${this.id}`, {
                //     trigger: true,
                // });
            },
        });
        this.renderSelectBoxes();
    },
    /**
     * Take the paths from the textarea, split it, create
     * a request queue and call a function that starts sending
     * one by one to be imported on the server.
     */
    importFromPathsClicked: function () {
        var preserve_dirs = this.modal.$el.find(".preserve-checkbox").is(":checked");
        var link_data = this.modal.$el.find(".link-checkbox").is(":checked");
        var space_to_tab = this.modal.$el.find(".spacetab-checkbox").is(":checked");
        var to_posix_lines = this.modal.$el.find(".posix-checkbox").is(":checked");
        var tag_using_filenames = this.modal.$el.find(".tag-files").is(":checked");
        var file_type = this.select_extension.value();
        var dbkey = this.select_genome.value();
        var paths = $("textarea#import_paths").val();
        var valid_paths = [];
        if (!paths) {
            Toast.info("Please enter a path relative to Galaxy root.");
        } else {
            this.modal.disableButton("Import");
            paths = paths.split("\n");
            for (let i = paths.length - 1; i >= 0; i--) {
                var trimmed = paths[i].trim();
                if (trimmed.length !== 0) {
                    valid_paths.push(trimmed);
                }
            }
            this.initChainCallControlAddingDatasets({
                length: valid_paths.length,
            });
            this.chainCallImportingFolders({
                paths: valid_paths,
                preserve_dirs: preserve_dirs,
                link_data: link_data,
                space_to_tab: space_to_tab,
                to_posix_lines: to_posix_lines,
                source: "admin_path",
                file_type: file_type,
                tag_using_filenames: tag_using_filenames,
                dbkey: dbkey,
            });
        }
    },
    /**
     * Take the array of paths and create a request for each of them
     * calling them in series. Update the progress bar in between each.
     * @param  {array} paths                    paths relative to Galaxy root folder
     * @param  {boolean} preserve_dirs          indicates whether to preserve folder structure
     * @param  {boolean} link_data              copy files to Galaxy or link instead
     * @param  {boolean} to_posix_lines         convert line endings to POSIX standard
     * @param  {boolean} space_to_tab           convert spaces to tabs
     * @param  {str} source                     string representing what type of folder
     *                                          is the source of import
     * @param  {boolean} tag_using_filenames    add tags to datasets using names of files
     */
    chainCallImportingFolders: function (options) {
        const Galaxy = getGalaxyInstance();
        // TODO need to check which paths to call
        const popped_item = options.paths.pop();
        if (typeof popped_item == "undefined") {
            if (this.options.chain_call_control.failed_number === 0) {
                Toast.success("Selected folders and their contents imported into the current folder.");
                Galaxy.modal.hide();
            } else {
                // TODO better error report
                Toast.error("An error occurred.");
            }
            return true;
        }
        const post_url = `${getAppRoot()}api/libraries/datasets`;
        const post_data = {
            encoded_folder_id: this.id,
            source: options.source,
            path: popped_item,
            preserve_dirs: options.preserve_dirs,
            link_data: options.link_data,
            to_posix_lines: options.to_posix_lines,
            space_to_tab: options.space_to_tab,
            file_type: options.file_type,
            dbkey: options.dbkey,
            tag_using_filenames: options.tag_using_filenames,
        };
        const promise = $.when($.post(post_url, post_data));
        promise
            .done((response) => {
                updateProgress();
                this.chainCallImportingFolders(options);
            })
            .fail(() => {
                this.options.chain_call_control.failed_number += 1;
                updateProgress();
                this.chainCallImportingFolders(options);
            });
    },
    templateAddingDatasetsProgressBar: function () {
        return _.template(
            `<div class="import_text">
                Adding selected datasets to library folder <b><%= _.escape(folder_name) %></b>
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0"
                    aria-valuemax="100" style="width: 00%;">
                    <span class="completion_span">0% Complete</span>
                </div>
            </div>`
        );
    },
    initChainCallControlAddingDatasets: function (options) {
        var template;
        template = this.templateAddingDatasetsProgressBar();
        this.modal.$el.find(".modal-body").html(
            template({
                folder_name: this.options.folder_name,
            })
        );

        // var progress_bar_tmpl = this.templateAddingDatasetsProgressBar();
        // this.modal.$el.find( '.modal-body' ).html( progress_bar_tmpl( { folder_name : this.options.folder_name } ) );
        this.progress = 0;
        this.progressStep = 100 / options.length;
        this.options.chain_call_control.total_number = options.length;
        this.options.chain_call_control.failed_number = 0;
    },

    /**
     * Take the array of hdas and create a request for each.
     * Call them in chain and update progress bar in between each.
     * @param  {array} hdas_set array of empty hda objects
     */
    chainCallAddingHdas: function (hdas_set) {
        const Galaxy = getGalaxyInstance();
        this.added_hdas = new mod_library_model.Folder();
        var popped_item = hdas_set.pop();
        if (typeof popped_item == "undefined") {
            if (this.options.chain_call_control.failed_number === 0) {
                Toast.success("Selected datasets from history added to the folder");
            } else if (this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number) {
                Toast.error("There was an error and no datasets were added to the folder.");
            } else if (this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number) {
                Toast.warning("Some of the datasets could not be added to the folder");
            }
            this.options.updateContent();
            Galaxy.modal.hide();
            return this.added_hdas;
        }
        var promise = $.when(
            popped_item.save({
                from_hda_id: popped_item.get("from_hda_id"),
            })
        );

        promise
            .done((model) => {
                // TODO add to lib
                // Galaxy.libraries.folderListView.collection.add(model);
                updateProgress();
                this.chainCallAddingHdas(hdas_set);
            })
            .fail(() => {
                this.options.chain_call_control.failed_number += 1;
                updateProgress();
                this.chainCallAddingHdas(hdas_set);
            });
    },
});
export default {
    AddDatasets: AddDatasets,
};
