import _l from "utils/localization";
/**
    This is the base class of the tool form plugin. This class is e.g. inherited by the regular and the workflow tool form.
*/
import Utils from "utils/utils";
import Deferred from "utils/deferred";
import Ui from "mvc/ui/ui-misc";
import FormBase from "mvc/form/form-view";
import Webhooks from "mvc/webhooks";
import Citations from "components/Citations.vue";
import Vue from "vue";
export default FormBase.extend({
    initialize: function(options) {
        var self = this;
        this.deferred = new Deferred();
        FormBase.prototype.initialize.call(this, options);

        // optional model update
        this._update(this.model.get("initialmodel"));

        // listen to history panel
        if (this.model.get("listen_to_history") && parent.Galaxy && parent.Galaxy.currHistoryPanel) {
            this.listenTo(parent.Galaxy.currHistoryPanel.collection, "change", () => {
                self.model.get("onchange")();
            });
        }
        // destroy dom elements
        this.$el.on("remove", () => {
            self._destroy();
        });
    },

    /** Allows tool form variation to update tool model */
    _update: function(callback) {
        var self = this;
        callback = callback || this.model.get("buildmodel");
        if (callback) {
            this.deferred.reset();
            this.deferred.execute(process => {
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
    _destroy: function() {
        var self = this;
        this.$el.off().hide();
        this.deferred.execute(() => {
            FormBase.prototype.remove.call(self);
            Galaxy.emit.debug("tool-form-base::_destroy()", "Destroy view.");
        });
    },

    /** Build form */
    _render: function() {
        var self = this;
        var options = this.model.attributes;
        this.model.set({
            title:
                options.fixed_title ||
                `<b>${options.name}</b> ${options.description} (Galaxy Version ${options.version})`,
            operations: !options.hide_operations && this._operations(),
            onchange: function() {
                self.deferred.reset();
                self.deferred.execute(process => {
                    self.model.get("postchange")(process, self);
                });
            }
        });
        this.render();
        if (!this.model.get("collapsible")) {
            this.$el.append(
                $("<div/>")
                    .addClass("ui-margin-top-large")
                    .append(this._footer())
            );
        }
        this.show_message &&
            this.message.update({
                status: "success",
                message: `Now you are using '${options.name}' version ${options.version}, id '${options.id}'.`,
                persistent: false
            });
        this.show_message = true;
    },

    /** Create tool operation menu */
    _operations: function() {
        var self = this;
        var options = this.model.attributes;

        // button for version selection
        var versions_button = new Ui.ButtonMenu({
            icon: "fa-cubes",
            title: (!options.narrow && "Versions") || null,
            tooltip: "Select another tool version"
        });
        if (!options.sustain_version && options.versions && options.versions.length > 1) {
            for (var i in options.versions) {
                var version = options.versions[i];
                if (version != options.version) {
                    versions_button.addMenu({
                        title: `Switch to ${version}`,
                        version: version,
                        icon: "fa-cube",
                        onclick: function() {
                            // here we update the tool version (some tools encode the version also in the id)
                            self.model.set("id", options.id.replace(options.version, this.version));
                            self.model.set("version", this.version);
                            self._update();
                        }
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
            title: (!options.narrow && "Options") || null,
            tooltip: "View available options"
        });
        if (options.biostar_url) {
            menu_button.addMenu({
                icon: "fa-question-circle",
                title: "Question?",
                onclick: function() {
                    window.open(`${options.biostar_url}/p/new/post/`);
                }
            });
            menu_button.addMenu({
                icon: "fa-search",
                title: _l("Search"),
                onclick: function() {
                    window.open(`${options.biostar_url}/local/search/page/?q=${options.name}`);
                }
            });
        }
        menu_button.addMenu({
            icon: "fa-share",
            title: _l("Share"),
            onclick: function() {
                prompt(
                    "Copy to clipboard: Ctrl+C, Enter",
                    `${window.location.origin + Galaxy.root}root?tool_id=${options.id}`
                );
            }
        });

        // add admin operations
        if (Galaxy.user && Galaxy.user.get("is_admin")) {
            menu_button.addMenu({
                icon: "fa-download",
                title: _l("Download"),
                onclick: function() {
                    window.location.href = `${Galaxy.root}api/tools/${options.id}/download`;
                }
            });
        }

        // button for version selection
        if (options.requirements && options.requirements.length > 0) {
            menu_button.addMenu({
                icon: "fa-info-circle",
                title: _l("Requirements"),
                onclick: function() {
                    if (!this.requirements_visible || self.portlet.collapsed) {
                        this.requirements_visible = true;
                        self.portlet.expand();
                        self.message.update({
                            persistent: true,
                            message: self._templateRequirements(options),
                            status: "info"
                        });
                    } else {
                        this.requirements_visible = false;
                        self.message.update({ message: "" });
                    }
                }
            });
        }

        // add toolshed url
        if (options.sharable_url) {
            menu_button.addMenu({
                icon: "fa-external-link",
                title: _l("See in Tool Shed"),
                onclick: function() {
                    window.open(options.sharable_url);
                }
            });
        }

        // add tool menu webhooks
        Webhooks.load({
            type: "tool-menu",
            callback: function(webhooks) {
                webhooks.each(model => {
                    var webhook = model.toJSON();
                    if (webhook.activate && webhook.config.function) {
                        menu_button.addMenu({
                            icon: webhook.config.icon,
                            title: webhook.config.title,
                            onclick: function() {
                                var func = new Function("options", webhook.config.function);
                                func(options);
                            }
                        });
                    }
                });
            }
        });

        return {
            menu: menu_button,
            versions: versions_button
        };
    },

    /** Create footer */
    _footer: function() {
        var options = this.model.attributes;
        var $el = $("<div/>").append(this._templateHelp(options));
        if (options.citations) {
            var citationInstance = Vue.extend(Citations);
            var vm = document.createElement("div");
            $el.append(vm);
            new citationInstance({
                propsData: {
                    id: options.id,
                    source: "tools"
                }
            }).$mount(vm);
        }
        return $el;
    },

    /** Templates */
    _templateHelp: function(options) {
        var $tmpl = $("<div/>")
            .addClass("ui-form-help")
            .append(options.help);
        $tmpl.find("a").attr("target", "_blank");
        $tmpl.find("img").each(function() {
            var img_src = $(this).attr("src");
            if (img_src.indexOf("admin_toolshed") !== -1) {
                $(this).attr("src", Galaxy.root + img_src);
            }
        });
        return $tmpl;
    },

    _templateRequirements: function(options) {
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
    }
});
