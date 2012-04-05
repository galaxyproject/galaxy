/**
 * Utility models and views for Galaxy objects.
 */

/**
 * Clickable button represented as an icon.
 */
var IconButton = Backbone.Model.extend({
    defaults: {
        title: "",
        icon_class: "",
        on_click: null
    }
});

var IconButtonCollection = Backbone.Collection.extend({
    model: IconButton
});

/**
 * A single icon button.
 */
var IconButtonView = Backbone.View.extend({
    tagName: 'a',
    className: 'icon-button menu-button',
    
    events: {
        'click': 'on_click'
    },
    
    render: function() {
        this.$el.attr('href', 'javascript:void(0)')
                .attr('title', this.model.attributes.title)
                .addClass(this.model.attributes.icon_class);
        return this;
    },
    
    on_click: function() {
        this.model.attributes.on_click();
    }
});

/**
 * Menu with multiple icon buttons.
 */
var IconButtonMenuView = Backbone.View.extend({
    tagName: 'div',
    
    render: function() {
        var self = this;
        this.collection.each(function(icon_button) {
            var view = new IconButtonView({model: icon_button});
            view.render();
            self.$el.append(view.$el); 
        });
        return this;
    }
});

/**
 * 
 */
var Grid = Backbone.Collection.extend({
    
});

/**
 *
 */
var GridView = Backbone.View.extend({
    
});


