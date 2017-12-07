$(document).ready(function() {

    var galaxyRoot = typeof Galaxy != 'undefined' ? Galaxy.root : '/';

    var PHDComicsAppView = Backbone.View.extend({
        el: '#phdcomics',

        appTemplate: _.template(
            '<div id="phdcomics-header">' +
                '<div id="phdcomics-name">PHD Comics</div>' +
                '<button id="phdcomics-random">Random</button>' +
            '</div>' +
            '<div id="phdcomics-img"></div>'
        ),

        imgTemplate: _.template('<img src="<%= src %>"">'),

        events: {
            'click #phdcomics-random': 'getRandomComic'
        },

        initialize: function() {
            this.render();
        },

        render: function() {
            this.$el.html(this.appTemplate());
            this.$comicImg = this.$('#phdcomics-img');
            this.getRandomComic();
            return this;
        },

        getRandomComic: function() {
            var me = this,
                url = galaxyRoot + 'api/webhooks/phdcomics/data';

            this.$comicImg.html($('<div/>', {
                id: 'phdcomics-loader'
            }));

            $.getJSON(url, function(data) {
                if (data.success) {
                    me.renderImg(data.src);
                } else {
                    console.error('[ERROR] "' + url + '":\n' + data.error);
                }
            });
        },

        renderImg: function(src) {
            this.$comicImg.html(this.imgTemplate({src: src}));
        }
    });

    new PHDComicsAppView();
});
