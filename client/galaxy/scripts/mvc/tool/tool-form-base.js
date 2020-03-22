/**
    This is the base class of the tool form plugin. This class is e.g. inherited by the regular and the workflow tool form.
*/
import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import ariaAlert from "utils/ariaAlert";
import Deferred from "utils/deferred";
import Ui from "mvc/ui/ui-misc";
import FormBase from "mvc/form/form-view";
import Webhooks from "mvc/webhooks";
import Citations from "components/Citations.vue";
import xrefs from "components/xrefs.vue";
import Vue from "vue";
import axios from "axios";

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
        this.model.set({
            title:
                options.fixed_title ||
                `<b>${options.name}</b> ${options.description} (Galaxy Version ${options.version})`,
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
            icon: "fa-share",
            title: _l("Share"),
            onclick: function () {
                prompt(
                    "Copy to clipboard: Ctrl+C, Enter",
                    `${window.location.origin + getAppRoot()}root?tool_id=${options.id}`
                );
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

        // button for version selection
        if (options.requirements && options.requirements.length > 0) {
            menu_button.addMenu({
                icon: "fa-info-circle",
                title: _l("Requirements"),
                onclick: function () {
                    if (!this.requirements_visible || self.portlet.collapsed) {
                        this.requirements_visible = true;
                        self.portlet.expand();
                        self.message.update({
                            persistent: true,
                            message: self._templateRequirements(options),
                            status: "info",
                        });
                    } else {
                        this.requirements_visible = false;
                        self.message.update({ message: "" });
                    }
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
        var options = this.model.attributes;
        var $el = $("<div/>").append(this._templateHelp(options));
        if (options.citations) {
            var citationInstance = Vue.extend(Citations);
            var vm = document.createElement("div");
            $el.append(vm);
            new citationInstance({
                propsData: {
                    id: options.id,
                    source: "tools",
                },
            }).$mount(vm);
        }
        if (options.xrefs && options.xrefs.length) {
            var xrefInstance = Vue.extend(xrefs);
            vm = document.createElement("div");
            $el.append(vm);
            new xrefInstance({
                propsData: {
                    id: options.id,
                    source: "tools",
                },
            }).$mount(vm);
        }
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

    _templateRequirements: function (options) {
        var nreq = options.requirements.length;
        if (nreq > 0) {
            var requirements_message = "This tool requires ";
            _.each(options.requirements, (req, i) => {
                requirements_message +=
                    req.name +
                    (req.version ? ` (Version ${req.version})` : "") +
                    (i < nreq - 2 ? ", " : i == nreq - 2 ? " and " : "");
            });
            var requirements_link = $("<a/>")
                .attr("target", "_blank")
                .attr("href", "https://galaxyproject.org/tools/requirements/")
                .text("here");
            return $("<span/>")
                .append(`${requirements_message}. Click `)
                .append(requirements_link)
                .append(" for more information.");
        }
        return "No requirements found.";
    },
});
