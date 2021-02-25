/**
    This is the base class of the tool form plugin. This class is e.g. inherited by the regular and the workflow tool form.
*/
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import ariaAlert from "utils/ariaAlert";
import Deferred from "utils/deferred";
import Ui from "mvc/ui/ui-misc";
import FormBase from "mvc/form/form-view";
import Webhooks from "mvc/webhooks";
import ToolFooter from "components/Tool/ToolFooter.vue";
import Vue from "vue";
import axios from "axios";
import { copy } from "utils/clipboard";

export default FormBase.extend({
    initialize: function (options) {
        const Galaxy = getGalaxyInstance();
        var self = this;
        this.deferred = new Deferred();
        FormBase.prototype.initialize.call(this, options);

        // optional model update
        this._update();

        // listen to history panel
        if (this.model.get("listen_to_history") && Galaxy.currHistoryPanel) {
            this.listenTo(Galaxy.currHistoryPanel.collection, "change", () => {
                self.model.get("onchange")();
            });
        }
        // destroy dom elements
        this.$el.on("remove", () => {
            self._destroy();
        });
    },

    /** Allows tool form variation to update tool model */
    _update: function () {
        var self = this;
        var callback = this.model.get("buildmodel");
        if (callback) {
            this.deferred.reset();
            this.deferred.execute((process) => {
                callback(process, self);
                process.then(() => {
                    self._render();
                });
            });
        } else {
            this._render();
        }
    },

    /** Wait for deferred build processes before removal */
    _destroy: function () {
        var self = this;
        this.$el.off().hide();
        this.deferred.execute(() => {
            FormBase.prototype.remove.call(self);
            const Galaxy = getGalaxyInstance();
            Galaxy.emit.debug("tool-form-base::_destroy()", "Destroy view.");
        });
    },

    /** Build form */
    _render: function () {
        var self = this;
        var options = this.model.attributes;
        if (options.setupToolMicrodata) {
            this.$el.attr("itemscope", "itemscope");
            this.$el.attr("itemtype", "https://schema.org/CreativeWork");
        }
        this.model.set({
            title:
                options.fixed_title ||
                `<b itemprop="name">${options.name}</b> <span itemprop="description">${options.description}</span> (Galaxy Version ${options.version})`,
            operations: !options.hide_operations && this._operations(),
            onchange: function () {
                self.deferred.reset();
                self.deferred.execute((process) => {
                    self.model.get("postchange")(process, self);
                });
            },
        });
        this.render();
        if (!this.model.get("collapsible")) {
            this.$el.append($("<div/>").addClass("mt-2").append(this._footer()));
        }
        options.tool_errors &&
            this.message.update({
                status: "danger",
                message: options.tool_errors,
                persistent: true,
            });
        this.show_message &&
            this.message.update({
                status: "success",
                message: `Now you are using '${options.name}' version ${options.version}, id '${options.id}'.`,
                persistent: false,
            });
        this.show_message = true;
    },

    /** Create tool operation menu */
    _operations: function () {
        var self = this;
        var options = this.model.attributes;
        const Galaxy = getGalaxyInstance();

        // Buttons for adding and removing favorite.
        const in_favorites = Galaxy.user.getFavorites().tools.indexOf(options.id) >= 0;
        var favorite_button = new Ui.Button({
            icon: "fa-star-o",
            title: options.narrow ? null : "Favorite",
            tooltip: "Add to favorites",
            visible: !Galaxy.user.isAnonymous() && !in_favorites,
            onclick: () => {
                axios
                    .put(`${Galaxy.root}api/users/${Galaxy.user.id}/favorites/tools`, { object_id: options.id })
                    .then((response) => {
                        favorite_button.hide();
                        remove_favorite_button.show();
                        Galaxy.user.updateFavorites("tools", response.data);
                        ariaAlert("added to favorites");
                    });
            },
        });

        var remove_favorite_button = new Ui.Button({
            icon: "fa-star",
            title: options.narrow ? null : "Added",
            tooltip: "Remove from favorites",
            visible: !Galaxy.user.isAnonymous() && in_favorites,
            onclick: () => {
                axios
                    .delete(
                        `${Galaxy.root}api/users/${Galaxy.user.id}/favorites/tools/${encodeURIComponent(options.id)}`
                    )
                    .then((response) => {
                        remove_favorite_button.hide();
                        favorite_button.show();
                        Galaxy.user.updateFavorites("tools", response.data);
                        ariaAlert("removed from favorites");
                    });
            },
        });

        // button for version selection
        var versions_button = new Ui.ButtonMenu({
            icon: "fa-cubes",
            cls: "btn btn-secondary float-right tool-versions",
            title: options.narrow ? null : "Versions",
            tooltip: "Select another tool version",
        });

        if (!options.sustain_version && options.versions && options.versions.length > 1) {
            for (var i in options.versions) {
                var version = options.versions[i];
                if (version != options.version) {
                    versions_button.addMenu({
                        title: `Switch to ${version}`,
                        version: version,
                        icon: "fa-cube",
                        onclick: function () {
                            // here we update the tool version (some tools encode the version also in the id)
                            self.model.set("id", options.id.replace(options.version, this.version));
                            self.model.set("version", this.version);
                            self.model.get("onchange")();
                            self._update();
                        },
                    });
                }
            }
        } else {
            versions_button.$el.hide();
        }

        // button for options e.g. search, help
        var menu_button = new Ui.ButtonMenu({
            id: "options",
            icon: "fa-caret-down",
            title: options.narrow ? null : "Options",
            tooltip: "View available options",
        });
        menu_button.addMenu({
            icon: "fa-chain",
            title: _l("Copy link"),
            onclick: function () {
                copy(
                    `${window.location.origin + getAppRoot()}root?tool_id=${options.id}`,
                    "Link was copied to your clipboard"
                );
            },
        });
        menu_button.addMenu({
            icon: "fa-files-o",
            title: _l("Copy tool ID"),
            onclick: function () {
                copy(`${options.id}`, "Tool ID was copied to your clipboard");
            },
        });

        // add admin operations
        if (Galaxy.user && Galaxy.user.get("is_admin")) {
            menu_button.addMenu({
                icon: "fa-download",
                title: _l("Download"),
                onclick: function () {
                    window.location.href = `${getAppRoot()}api/tools/${options.id}/download`;
                },
            });
        }

        // add toolshed url
        if (options.sharable_url) {
            menu_button.addMenu({
                icon: "fa-external-link",
                title: _l("See in Tool Shed"),
                onclick: function () {
                    window.open(options.sharable_url);
                },
            });
        }

        // add tool menu webhooks
        Webhooks.load({
            type: "tool-menu",
            callback: function (webhooks) {
                webhooks.each((model) => {
                    var webhook = model.toJSON();
                    if (webhook.activate && webhook.config.function) {
                        menu_button.addMenu({
                            icon: webhook.config.icon,
                            title: webhook.config.title,
                            onclick: function () {
                                var func = new Function("options", webhook.config.function);
                                func(options);
                            },
                        });
                    }
                });
            },
        });

        return {
            menu: menu_button,
            versions: versions_button,
            favorite: favorite_button,
            remove_favorite: remove_favorite_button,
        };
    },

    /** Create footer */
    _footer: function () {
        const options = this.model.attributes;
        const $el = $("<div/>").append(this._templateHelp(options));
        const toolFooterInstance = Vue.extend(ToolFooter);
        const vm = document.createElement("div");
        $el.append(vm);
        const propsData = {
            id: options.id,
            hasCitations: options.citations,
            xrefs: options.xrefs,
            license: options.license,
            creators: options.creator,
            requirements: options.requirements,
        };
        new toolFooterInstance({
            propsData,
        }).$mount(vm);
        return $el;
    },

    /** Templates */
    _templateHelp: function (options) {
        var $tmpl = $("<div/>").addClass("form-help form-text mt-4").append(options.help);
        $tmpl.find("a").attr("target", "_blank");
        $tmpl.find("img").each(function () {
            var img_src = $(this).attr("src");
            if (img_src.indexOf("admin_toolshed") !== -1) {
                $(this).attr("src", getAppRoot() + img_src);
            }
        });
        return $tmpl;
    },
});
