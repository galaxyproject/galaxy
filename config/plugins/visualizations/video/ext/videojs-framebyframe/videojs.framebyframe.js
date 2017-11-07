// videojs-framebyframe-plugin

var VjsButton = videojs.getComponent('Button');
var FBFButton = videojs.extend(VjsButton, {
    constructor: function(player, options) {
        VjsButton.call(this, player, options);
        this.player = player;
        this.frameTime = 1/options.fps;
        this.step_size = options.value;
        this.on('click', this.onClick);
    },

    onClick: function() {
        // Start by pausing the player
        this.player.pause();
        // Calculate movement distance
        var dist = this.frameTime * this.step_size;
        this.player.currentTime(this.player.currentTime() + dist);
    },
});

function framebyframe(options) {
    var player = this,
        frameTime = 1 / 30; // assume 30 fps

    player.ready(function() {
        options.steps.forEach(function(opt) {
            player.controlBar.addChild(
                new FBFButton(player, {
                    el: videojs.createEl(
                        'button',
                        {
                            className: 'vjs-res-button vjs-control',
                            innerHTML: '<div class="vjs-control-content" style="font-size: 11px; line-height: 28px;"><span class="vjs-fbf">' + opt.text + '</span></div>'
                        },
                        {
                            role: 'button'
                        }
                    ),
                    value: opt.step,
                    fps: options.fps,
                }),
            {}, opt.index);
        });
    });
}
videojs.plugin('framebyframe', framebyframe);
