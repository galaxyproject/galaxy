define([ "utils/utils", "mvc/ui/ui-misc", "mvc/ui/ui-tabs" ], function(Utils, Ui, Tabs) {
    var View = Backbone.View.extend({
        events: {
            "click .ui-thumbnails-item": "_onclick",
            "dblclick .ui-thumbnails-item": "_ondblclick"
        },
        initialize: function(options) {
            this.model = options.model || new Backbone.Model(options), this.collection = new Backbone.Collection(this.model.get("collection")), 
            this.tabs = new Tabs.View({}), this.setElement(this.tabs.$el.addClass("ui-thumbnails")), 
            this.render(), this.listenTo(this.model, "change", this.render, this), this.listenTo(this.collection, "reset change add remove", this.render, this);
        },
        render: function() {
            this.first = null, this.tabs.delAll(), this._renderDefault(), this._renderList();
        },
        _renderDefault: function() {
            var self = this, title_length = 20, $el = $("<div/>").addClass("ui-thumbnails-grid");
            this.collection.each(function(model) {
                if (-1 !== model.get("keywords").indexOf("default")) {
                    var title = model.get("title");
                    $el.append($(self._templateThumbnailItem({
                        id: model.id,
                        title: title.length < title_length ? title : title.substr(0, title_length) + "...",
                        title_icon: model.get("title_icon"),
                        image_src: model.get("image_src")
                    })).tooltip({
                        title: model.get("description"),
                        placement: "bottom"
                    }));
                }
            }), $el.children().length > 0 && this.tabs.add({
                id: Utils.uid(),
                title: self.model.get("title_default"),
                $el: $el
            });
        },
        _renderList: function() {
            var self = this;
            if (this.collection.length > 0) {
                this.first = this.first || this.collection.first().id;
                var $el = $("<div/>").addClass("ui-thumbnails-grid");
                this.collection.each(function(model) {
                    $el.append(self._templateRegularItem(model.attributes));
                }), this.tabs.add({
                    id: Utils.uid(),
                    title: self.model.get("title_list"),
                    $el: $el
                });
            }
        },
        value: function(new_value) {
            if (void 0 !== new_value) {
                new_value = "__first" == new_value ? this.first : new_value;
                var before = this.$(".ui-thumbnail-current").attr("value");
                this.$(".ui-thumbnail-current").removeClass("ui-thumbnail-current"), this.$('[value="' + new_value + '"]').addClass("ui-thumbnail-current");
                var after = this.$(".ui-thumbnail-current").attr("value"), change_handler = this.model.get("onchange");
                after != before && change_handler && change_handler(after);
            }
            return this.$(".ui-thumbnail-current").attr("value");
        },
        _onclick: function(e) {
            this.value($(e.target).closest(".ui-thumbnails-item").attr("value"));
        },
        _ondblclick: function() {
            this.model.get("ondblclick") && this.model.get("ondblclick")(this.value());
        },
        _templateThumbnailItem: function(options) {
            return '<div class="ui-thumbnails-item ui-thumbnails-item-float" value="' + options.id + '"><img class="ui-thumbnails-image" src="' + options.image_src + '"><div class="ui-thumbnails-title ui-form-info"><span class="fa ' + options.title_icon + '"/>' + options.title + "</div><div>";
        },
        _templateRegularItem: function(options) {
            return '<div class="ui-thumbnails-item" value="' + options.id + '"><table><tr><td><img class="ui-thumbnails-image" src="' + options.image_src + '"></td><td><div class="ui-thumbnails-description-title ui-form-info">' + options.title + '</div><div class="ui-thumbnails-description-text ui-form-info">' + options.description + "</div></td></tr><div>";
        }
    });
    return {
        View: View
    };
});