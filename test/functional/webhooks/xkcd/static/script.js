$(document).ready(function() {

    var XkcdAppView = Backbone.View.extend({
        el: '#xkcd',

        appTemplate: _.template(
            '<div id="xkcd-header">' +
                '<div id="xkcd-name">xkcd</div>' +
                '<button id="xkcd-random">Random</button>' +
            '</div>' +
            '<div id="xkcd-img"></div>'
        ),

        imgTemplate: _.template('<img src="<%= img %>" alt="<%= alt %>" title="<%= title %>">'),

        events: {
            'click #xkcd-random': 'getRandomXkcd'
        },

        initialize: function() {
            var me = this;

            this.render();

            // Get id of the last xkcd
            $.getJSON('http://dynamic.xkcd.com/api-0/jsonp/comic?callback=?', function(data) {
                me.latestXkcdId = data.num;
                me.getRandomXkcd();
            });
        },

        render: function() {
            this.$el.html(this.appTemplate());
            this.xkcdImg = this.$('#xkcd-img');
            return this;
        },

        getRandomXkcd: function() {
            var me = this,
                randomId = Math.floor(Math.random() * this.latestXkcdId) + 1;

            this.xkcdImg.html($('<div/>', {id: 'xkcd-loader'}));
            $.getJSON('http://dynamic.xkcd.com/api-0/jsonp/comic/' + randomId + '?callback=?', function(data) {
                me.xkcd = {img: data.img, alt: data.alt, title: data.title};
                me.renderImg();
            });
        },

        renderImg: function() {
            this.xkcdImg.html(this.imgTemplate({img: this.xkcd.img, alt: this.xkcd.alt, title: this.xkcd.title}));
        }
    });

    var XkcdApp = new XkcdAppView;

});
