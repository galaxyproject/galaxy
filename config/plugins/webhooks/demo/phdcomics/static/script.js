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
            'click #phdcomics-random': 'getRandomPHDComics'
        },

        initialize: function() {
            this.render();
        },

        render: function() {
            this.$el.html(this.appTemplate());
            this.phdComicsImg = this.$('#phdcomics-img');
            this.getRandomPHDComics();
            return this;
        },

        getRandomPHDComics: function() {
            var me = this,
                url = galaxyRoot + 'api/webhooks/phdcomics/get_data';

            this.phdComicsImg.html($('<div/>', {id: 'phdcomics-loader'}));
            $.getJSON(url, function(data) {
                if (data.success) {
                    me.phdComics = {src: data.data.src};
                    me.renderImg();
                } else {
                    console.log('[ERROR] "' + url + '":\n' + data.error);
                }
            });
        },

        renderImg: function() {
            this.phdComicsImg.html(this.imgTemplate({src: this.phdComics.src}));
        }
    });

    var PHDComicsApp = new PHDComicsAppView;

});
