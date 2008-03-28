#!/usr/bin/env python

import sys
import Image
import ImageColor

assert sys.version_info[:2] >= ( 2, 4 )

over = Image.open( sys.argv[1] )
color = ImageColor.getrgb( sys.argv[2] )

new = Image.new( 'RGBA', over.size, color )

# 'Over' is passed twice since it has an alpha channel -- it is it's own mask
new.paste( over, over )

new.save( sys.argv[3] )