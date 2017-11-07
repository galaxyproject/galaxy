# Galaxy Video Viz Plugin

This plugin allows for viewing of videos (mp4 files) directly in the galaxy interface.

Galaxy, now with cute cat videos

![cat videos](http://i.imgur.com/CxsDze3.png)

# Requirements

This library depends on the `mp4` [datatype](http://toolshed.g2.bx.psu.edu/view/eric-rasche/video_datatypes) which will eventually be replaced by a better implementation that isn't a complete hack.

# Design

It is powered by [video.js](https://github.com/videojs/video.js/), with two
plugins: [speed controls](https://github.com/nicetip/videojs-speed), and
[frame-by-frame](https://github.com/erasche/videojs-framebyframe) controls to
allow stepping through a video in increments.

# Installation

Installation is slightly more complicated than normal, because I use git and
submodules so as to track upstream repositories

```bash
git clone https://github.com/galaxyproject/tools-iuc
cd tools-iuc
# Not merged yet, so check out the branch
git checkout video-viz
# Update submodules
git submodule init
git submodule update
cp -Rv visualizations/video/  $GALAXY_ROOT/config/plugins/visualizations/
```

The submodules are stored in the `ext/` folder. At this point, you should be
ready to upload a video file and watch it through galaxy.

# Known Bugs

Currently does not support playback of anything but mp4 files. This is
hardcoded, and will change eventually.
