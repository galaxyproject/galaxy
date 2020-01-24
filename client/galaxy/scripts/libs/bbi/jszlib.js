/* -*- mode: javascript; c-basic-offset: 4; indent-tabs-mode: nil -*- */

//
// Javascript ZLib
// By Thomas Down 2010-2011
//
// Based very heavily on portions of jzlib (by ymnk@jcraft.com), who in
// turn credits Jean-loup Gailly and Mark Adler for the original zlib code.
//
// inflate.js: ZLib inflate code
//

//
// Shared constants
//

define([],function() {

var MAX_WBITS=15; // 32K LZ77 window
var DEF_WBITS=MAX_WBITS;
var MAX_MEM_LEVEL=9;
var MANY=1440;
var BMAX = 15;

// preset dictionary flag in zlib header
var PRESET_DICT=0x20;

var Z_NO_FLUSH=0;
var Z_PARTIAL_FLUSH=1;
var Z_SYNC_FLUSH=2;
var Z_FULL_FLUSH=3;
var Z_FINISH=4;

var Z_DEFLATED=8;

var Z_OK=0;
var Z_STREAM_END=1;
var Z_NEED_DICT=2;
var Z_ERRNO=-1;
var Z_STREAM_ERROR=-2;
var Z_DATA_ERROR=-3;
var Z_MEM_ERROR=-4;
var Z_BUF_ERROR=-5;
var Z_VERSION_ERROR=-6;

var METHOD=0;   // waiting for method byte
var FLAG=1;     // waiting for flag byte
var DICT4=2;    // four dictionary check bytes to go
var DICT3=3;    // three dictionary check bytes to go
var DICT2=4;    // two dictionary check bytes to go
var DICT1=5;    // one dictionary check byte to go
var DICT0=6;    // waiting for inflateSetDictionary
var BLOCKS=7;   // decompressing blocks
var CHECK4=8;   // four check bytes to go
var CHECK3=9;   // three check bytes to go
var CHECK2=10;  // two check bytes to go
var CHECK1=11;  // one check byte to go
var DONE=12;    // finished check, done
var BAD=13;     // got an error--stay here

var inflate_mask = [0x00000000, 0x00000001, 0x00000003, 0x00000007, 0x0000000f, 0x0000001f, 0x0000003f, 0x0000007f, 0x000000ff, 0x000001ff, 0x000003ff, 0x000007ff, 0x00000fff, 0x00001fff, 0x00003fff, 0x00007fff, 0x0000ffff];

var IB_TYPE=0;  // get type bits (3, including end bit)
var IB_LENS=1;  // get lengths for stored
var IB_STORED=2;// processing stored block
var IB_TABLE=3; // get table lengths
var IB_BTREE=4; // get bit lengths tree for a dynamic block
var IB_DTREE=5; // get length, distance trees for a dynamic block
var IB_CODES=6; // processing fixed or dynamic block
var IB_DRY=7;   // output remaining window bytes
var IB_DONE=8;  // finished last block, done
var IB_BAD=9;   // ot a data error--stuck here

var fixed_bl = 9;
var fixed_bd = 5;

var fixed_tl = [
    96,7,256, 0,8,80, 0,8,16, 84,8,115,
    82,7,31, 0,8,112, 0,8,48, 0,9,192,
    80,7,10, 0,8,96, 0,8,32, 0,9,160,
    0,8,0, 0,8,128, 0,8,64, 0,9,224,
    80,7,6, 0,8,88, 0,8,24, 0,9,144,
    83,7,59, 0,8,120, 0,8,56, 0,9,208,
    81,7,17, 0,8,104, 0,8,40, 0,9,176,
    0,8,8, 0,8,136, 0,8,72, 0,9,240,
    80,7,4, 0,8,84, 0,8,20, 85,8,227,
    83,7,43, 0,8,116, 0,8,52, 0,9,200,
    81,7,13, 0,8,100, 0,8,36, 0,9,168,
    0,8,4, 0,8,132, 0,8,68, 0,9,232,
    80,7,8, 0,8,92, 0,8,28, 0,9,152,
    84,7,83, 0,8,124, 0,8,60, 0,9,216,
    82,7,23, 0,8,108, 0,8,44, 0,9,184,
    0,8,12, 0,8,140, 0,8,76, 0,9,248,
    80,7,3, 0,8,82, 0,8,18, 85,8,163,
    83,7,35, 0,8,114, 0,8,50, 0,9,196,
    81,7,11, 0,8,98, 0,8,34, 0,9,164,
    0,8,2, 0,8,130, 0,8,66, 0,9,228,
    80,7,7, 0,8,90, 0,8,26, 0,9,148,
    84,7,67, 0,8,122, 0,8,58, 0,9,212,
    82,7,19, 0,8,106, 0,8,42, 0,9,180,
    0,8,10, 0,8,138, 0,8,74, 0,9,244,
    80,7,5, 0,8,86, 0,8,22, 192,8,0,
    83,7,51, 0,8,118, 0,8,54, 0,9,204,
    81,7,15, 0,8,102, 0,8,38, 0,9,172,
    0,8,6, 0,8,134, 0,8,70, 0,9,236,
    80,7,9, 0,8,94, 0,8,30, 0,9,156,
    84,7,99, 0,8,126, 0,8,62, 0,9,220,
    82,7,27, 0,8,110, 0,8,46, 0,9,188,
    0,8,14, 0,8,142, 0,8,78, 0,9,252,
    96,7,256, 0,8,81, 0,8,17, 85,8,131,
    82,7,31, 0,8,113, 0,8,49, 0,9,194,
    80,7,10, 0,8,97, 0,8,33, 0,9,162,
    0,8,1, 0,8,129, 0,8,65, 0,9,226,
    80,7,6, 0,8,89, 0,8,25, 0,9,146,
    83,7,59, 0,8,121, 0,8,57, 0,9,210,
    81,7,17, 0,8,105, 0,8,41, 0,9,178,
    0,8,9, 0,8,137, 0,8,73, 0,9,242,
    80,7,4, 0,8,85, 0,8,21, 80,8,258,
    83,7,43, 0,8,117, 0,8,53, 0,9,202,
    81,7,13, 0,8,101, 0,8,37, 0,9,170,
    0,8,5, 0,8,133, 0,8,69, 0,9,234,
    80,7,8, 0,8,93, 0,8,29, 0,9,154,
    84,7,83, 0,8,125, 0,8,61, 0,9,218,
    82,7,23, 0,8,109, 0,8,45, 0,9,186,
    0,8,13, 0,8,141, 0,8,77, 0,9,250,
    80,7,3, 0,8,83, 0,8,19, 85,8,195,
    83,7,35, 0,8,115, 0,8,51, 0,9,198,
    81,7,11, 0,8,99, 0,8,35, 0,9,166,
    0,8,3, 0,8,131, 0,8,67, 0,9,230,
    80,7,7, 0,8,91, 0,8,27, 0,9,150,
    84,7,67, 0,8,123, 0,8,59, 0,9,214,
    82,7,19, 0,8,107, 0,8,43, 0,9,182,
    0,8,11, 0,8,139, 0,8,75, 0,9,246,
    80,7,5, 0,8,87, 0,8,23, 192,8,0,
    83,7,51, 0,8,119, 0,8,55, 0,9,206,
    81,7,15, 0,8,103, 0,8,39, 0,9,174,
    0,8,7, 0,8,135, 0,8,71, 0,9,238,
    80,7,9, 0,8,95, 0,8,31, 0,9,158,
    84,7,99, 0,8,127, 0,8,63, 0,9,222,
    82,7,27, 0,8,111, 0,8,47, 0,9,190,
    0,8,15, 0,8,143, 0,8,79, 0,9,254,
    96,7,256, 0,8,80, 0,8,16, 84,8,115,
    82,7,31, 0,8,112, 0,8,48, 0,9,193,

    80,7,10, 0,8,96, 0,8,32, 0,9,161,
    0,8,0, 0,8,128, 0,8,64, 0,9,225,
    80,7,6, 0,8,88, 0,8,24, 0,9,145,
    83,7,59, 0,8,120, 0,8,56, 0,9,209,
    81,7,17, 0,8,104, 0,8,40, 0,9,177,
    0,8,8, 0,8,136, 0,8,72, 0,9,241,
    80,7,4, 0,8,84, 0,8,20, 85,8,227,
    83,7,43, 0,8,116, 0,8,52, 0,9,201,
    81,7,13, 0,8,100, 0,8,36, 0,9,169,
    0,8,4, 0,8,132, 0,8,68, 0,9,233,
    80,7,8, 0,8,92, 0,8,28, 0,9,153,
    84,7,83, 0,8,124, 0,8,60, 0,9,217,
    82,7,23, 0,8,108, 0,8,44, 0,9,185,
    0,8,12, 0,8,140, 0,8,76, 0,9,249,
    80,7,3, 0,8,82, 0,8,18, 85,8,163,
    83,7,35, 0,8,114, 0,8,50, 0,9,197,
    81,7,11, 0,8,98, 0,8,34, 0,9,165,
    0,8,2, 0,8,130, 0,8,66, 0,9,229,
    80,7,7, 0,8,90, 0,8,26, 0,9,149,
    84,7,67, 0,8,122, 0,8,58, 0,9,213,
    82,7,19, 0,8,106, 0,8,42, 0,9,181,
    0,8,10, 0,8,138, 0,8,74, 0,9,245,
    80,7,5, 0,8,86, 0,8,22, 192,8,0,
    83,7,51, 0,8,118, 0,8,54, 0,9,205,
    81,7,15, 0,8,102, 0,8,38, 0,9,173,
    0,8,6, 0,8,134, 0,8,70, 0,9,237,
    80,7,9, 0,8,94, 0,8,30, 0,9,157,
    84,7,99, 0,8,126, 0,8,62, 0,9,221,
    82,7,27, 0,8,110, 0,8,46, 0,9,189,
    0,8,14, 0,8,142, 0,8,78, 0,9,253,
    96,7,256, 0,8,81, 0,8,17, 85,8,131,
    82,7,31, 0,8,113, 0,8,49, 0,9,195,
    80,7,10, 0,8,97, 0,8,33, 0,9,163,
    0,8,1, 0,8,129, 0,8,65, 0,9,227,
    80,7,6, 0,8,89, 0,8,25, 0,9,147,
    83,7,59, 0,8,121, 0,8,57, 0,9,211,
    81,7,17, 0,8,105, 0,8,41, 0,9,179,
    0,8,9, 0,8,137, 0,8,73, 0,9,243,
    80,7,4, 0,8,85, 0,8,21, 80,8,258,
    83,7,43, 0,8,117, 0,8,53, 0,9,203,
    81,7,13, 0,8,101, 0,8,37, 0,9,171,
    0,8,5, 0,8,133, 0,8,69, 0,9,235,
    80,7,8, 0,8,93, 0,8,29, 0,9,155,
    84,7,83, 0,8,125, 0,8,61, 0,9,219,
    82,7,23, 0,8,109, 0,8,45, 0,9,187,
    0,8,13, 0,8,141, 0,8,77, 0,9,251,
    80,7,3, 0,8,83, 0,8,19, 85,8,195,
    83,7,35, 0,8,115, 0,8,51, 0,9,199,
    81,7,11, 0,8,99, 0,8,35, 0,9,167,
    0,8,3, 0,8,131, 0,8,67, 0,9,231,
    80,7,7, 0,8,91, 0,8,27, 0,9,151,
    84,7,67, 0,8,123, 0,8,59, 0,9,215,
    82,7,19, 0,8,107, 0,8,43, 0,9,183,
    0,8,11, 0,8,139, 0,8,75, 0,9,247,
    80,7,5, 0,8,87, 0,8,23, 192,8,0,
    83,7,51, 0,8,119, 0,8,55, 0,9,207,
    81,7,15, 0,8,103, 0,8,39, 0,9,175,
    0,8,7, 0,8,135, 0,8,71, 0,9,239,
    80,7,9, 0,8,95, 0,8,31, 0,9,159,
    84,7,99, 0,8,127, 0,8,63, 0,9,223,
    82,7,27, 0,8,111, 0,8,47, 0,9,191,
    0,8,15, 0,8,143, 0,8,79, 0,9,255
];
var fixed_td = [
    80,5,1, 87,5,257, 83,5,17, 91,5,4097,
    81,5,5, 89,5,1025, 85,5,65, 93,5,16385,
    80,5,3, 88,5,513, 84,5,33, 92,5,8193,
    82,5,9, 90,5,2049, 86,5,129, 192,5,24577,
    80,5,2, 87,5,385, 83,5,25, 91,5,6145,
    81,5,7, 89,5,1537, 85,5,97, 93,5,24577,
    80,5,4, 88,5,769, 84,5,49, 92,5,12289,
    82,5,13, 90,5,3073, 86,5,193, 192,5,24577
];

  // Tables for deflate from PKZIP's appnote.txt.
  var cplens = [ // Copy lengths for literal codes 257..285
        3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31,
        35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258, 0, 0
  ];

  // see note #13 above about 258
  var cplext = [ // Extra bits for literal codes 257..285
        0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
        3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0, 112, 112  // 112==invalid
  ];

 var cpdist = [ // Copy offsets for distance codes 0..29
        1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193,
        257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145,
        8193, 12289, 16385, 24577
  ];

  var cpdext = [ // Extra bits for distance codes
        0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
        7, 7, 8, 8, 9, 9, 10, 10, 11, 11,
        12, 12, 13, 13];

//
// ZStream.java
//

function ZStream() {
}


ZStream.prototype.inflateInit = function(w, nowrap) {
    if (!w) {
	w = DEF_WBITS;
    }
    if (nowrap) {
	nowrap = false;
    }
    this.istate = new Inflate();
    return this.istate.inflateInit(this, nowrap?-w:w);
}

ZStream.prototype.inflate = function(f) {
    if(this.istate==null) return Z_STREAM_ERROR;
    return this.istate.inflate(this, f);
}

ZStream.prototype.inflateEnd = function(){
    if(this.istate==null) return Z_STREAM_ERROR;
    var ret=istate.inflateEnd(this);
    this.istate = null;
    return ret;
}
ZStream.prototype.inflateSync = function(){
    // if(istate == null) return Z_STREAM_ERROR;
    return istate.inflateSync(this);
}
ZStream.prototype.inflateSetDictionary = function(dictionary, dictLength){
    // if(istate == null) return Z_STREAM_ERROR;
    return istate.inflateSetDictionary(this, dictionary, dictLength);
}

/*

  public int deflateInit(int level){
    return deflateInit(level, MAX_WBITS);
  }
  public int deflateInit(int level, boolean nowrap){
    return deflateInit(level, MAX_WBITS, nowrap);
  }
  public int deflateInit(int level, int bits){
    return deflateInit(level, bits, false);
  }
  public int deflateInit(int level, int bits, boolean nowrap){
    dstate=new Deflate();
    return dstate.deflateInit(this, level, nowrap?-bits:bits);
  }
  public int deflate(int flush){
    if(dstate==null){
      return Z_STREAM_ERROR;
    }
    return dstate.deflate(this, flush);
  }
  public int deflateEnd(){
    if(dstate==null) return Z_STREAM_ERROR;
    int ret=dstate.deflateEnd();
    dstate=null;
    return ret;
  }
  public int deflateParams(int level, int strategy){
    if(dstate==null) return Z_STREAM_ERROR;
    return dstate.deflateParams(this, level, strategy);
  }
  public int deflateSetDictionary (byte[] dictionary, int dictLength){
    if(dstate == null)
      return Z_STREAM_ERROR;
    return dstate.deflateSetDictionary(this, dictionary, dictLength);
  }

*/

/*
  // Flush as much pending output as possible. All deflate() output goes
  // through this function so some applications may wish to modify it
  // to avoid allocating a large strm->next_out buffer and copying into it.
  // (See also read_buf()).
  void flush_pending(){
    int len=dstate.pending;

    if(len>avail_out) len=avail_out;
    if(len==0) return;

    if(dstate.pending_buf.length<=dstate.pending_out ||
       next_out.length<=next_out_index ||
       dstate.pending_buf.length<(dstate.pending_out+len) ||
       next_out.length<(next_out_index+len)){
      System.out.println(dstate.pending_buf.length+", "+dstate.pending_out+
			 ", "+next_out.length+", "+next_out_index+", "+len);
      System.out.println("avail_out="+avail_out);
    }

    System.arraycopy(dstate.pending_buf, dstate.pending_out,
		     next_out, next_out_index, len);

    next_out_index+=len;
    dstate.pending_out+=len;
    total_out+=len;
    avail_out-=len;
    dstate.pending-=len;
    if(dstate.pending==0){
      dstate.pending_out=0;
    }
  }

  // Read a new buffer from the current input stream, update the adler32
  // and total number of bytes read.  All deflate() input goes through
  // this function so some applications may wish to modify it to avoid
  // allocating a large strm->next_in buffer and copying from it.
  // (See also flush_pending()).
  int read_buf(byte[] buf, int start, int size) {
    int len=avail_in;

    if(len>size) len=size;
    if(len==0) return 0;

    avail_in-=len;

    if(dstate.noheader==0) {
      adler=_adler.adler32(adler, next_in, next_in_index, len);
    }
    System.arraycopy(next_in, next_in_index, buf, start, len);
    next_in_index  += len;
    total_in += len;
    return len;
  }

  public void free(){
    next_in=null;
    next_out=null;
    msg=null;
    _adler=null;
  }
}
*/


//
// Inflate.java
//

function Inflate() {
    this.was = [0];
}

Inflate.prototype.inflateReset = function(z) {
    if(z == null || z.istate == null) return Z_STREAM_ERROR;

    z.total_in = z.total_out = 0;
    z.msg = null;
    z.istate.mode = z.istate.nowrap!=0 ? BLOCKS : METHOD;
    z.istate.blocks.reset(z, null);
    return Z_OK;
}

Inflate.prototype.inflateEnd = function(z){
    if(this.blocks != null)
      this.blocks.free(z);
    this.blocks=null;
    return Z_OK;
}

Inflate.prototype.inflateInit = function(z, w){
    z.msg = null;
    this.blocks = null;

    // handle undocumented nowrap option (no zlib header or check)
    nowrap = 0;
    if(w < 0){
      w = - w;
      nowrap = 1;
    }

    // set window size
    if(w<8 ||w>15){
      this.inflateEnd(z);
      return Z_STREAM_ERROR;
    }
    this.wbits=w;

    z.istate.blocks=new InfBlocks(z,
				  z.istate.nowrap!=0 ? null : this,
				  1<<w);

    // reset state
    this.inflateReset(z);
    return Z_OK;
  }

Inflate.prototype.inflate = function(z, f){
    var r, b;

    if(z == null || z.istate == null || z.next_in == null)
      return Z_STREAM_ERROR;
    f = f == Z_FINISH ? Z_BUF_ERROR : Z_OK;
    r = Z_BUF_ERROR;
    while (true){
      switch (z.istate.mode){
      case METHOD:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        if(((z.istate.method = z.next_in[z.next_in_index++])&0xf)!=Z_DEFLATED){
          z.istate.mode = BAD;
          z.msg="unknown compression method";
          z.istate.marker = 5;       // can't try inflateSync
          break;
        }
        if((z.istate.method>>4)+8>z.istate.wbits){
          z.istate.mode = BAD;
          z.msg="invalid window size";
          z.istate.marker = 5;       // can't try inflateSync
          break;
        }
        z.istate.mode=FLAG;
      case FLAG:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        b = (z.next_in[z.next_in_index++])&0xff;

        if((((z.istate.method << 8)+b) % 31)!=0){
          z.istate.mode = BAD;
          z.msg = "incorrect header check";
          z.istate.marker = 5;       // can't try inflateSync
          break;
        }

        if((b&PRESET_DICT)==0){
          z.istate.mode = BLOCKS;
          break;
        }
        z.istate.mode = DICT4;
      case DICT4:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need=((z.next_in[z.next_in_index++]&0xff)<<24)&0xff000000;
        z.istate.mode=DICT3;
      case DICT3:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need+=((z.next_in[z.next_in_index++]&0xff)<<16)&0xff0000;
        z.istate.mode=DICT2;
      case DICT2:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need+=((z.next_in[z.next_in_index++]&0xff)<<8)&0xff00;
        z.istate.mode=DICT1;
      case DICT1:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need += (z.next_in[z.next_in_index++]&0xff);
        z.adler = z.istate.need;
        z.istate.mode = DICT0;
        return Z_NEED_DICT;
      case DICT0:
        z.istate.mode = BAD;
        z.msg = "need dictionary";
        z.istate.marker = 0;       // can try inflateSync
        return Z_STREAM_ERROR;
      case BLOCKS:

        r = z.istate.blocks.proc(z, r);
        if(r == Z_DATA_ERROR){
          z.istate.mode = BAD;
          z.istate.marker = 0;     // can try inflateSync
          break;
        }
        if(r == Z_OK){
          r = f;
        }
        if(r != Z_STREAM_END){
          return r;
        }
        r = f;
        z.istate.blocks.reset(z, z.istate.was);
        if(z.istate.nowrap!=0){
          z.istate.mode=DONE;
          break;
        }
        z.istate.mode=CHECK4;
      case CHECK4:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need=((z.next_in[z.next_in_index++]&0xff)<<24)&0xff000000;
        z.istate.mode=CHECK3;
      case CHECK3:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need+=((z.next_in[z.next_in_index++]&0xff)<<16)&0xff0000;
        z.istate.mode = CHECK2;
      case CHECK2:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need+=((z.next_in[z.next_in_index++]&0xff)<<8)&0xff00;
        z.istate.mode = CHECK1;
      case CHECK1:

        if(z.avail_in==0)return r;r=f;

        z.avail_in--; z.total_in++;
        z.istate.need+=(z.next_in[z.next_in_index++]&0xff);

        if(((z.istate.was[0])) != ((z.istate.need))){
          z.istate.mode = BAD;
          z.msg = "incorrect data check";
          z.istate.marker = 5;       // can't try inflateSync
          break;
        }

        z.istate.mode = DONE;
      case DONE:
        return Z_STREAM_END;
      case BAD:
        return Z_DATA_ERROR;
      default:
        return Z_STREAM_ERROR;
      }
    }
  }


Inflate.prototype.inflateSetDictionary = function(z,  dictionary, dictLength) {
    var index=0;
    var length = dictLength;
    if(z==null || z.istate == null|| z.istate.mode != DICT0)
      return Z_STREAM_ERROR;

    if(z._adler.adler32(1, dictionary, 0, dictLength)!=z.adler){
      return Z_DATA_ERROR;
    }

    z.adler = z._adler.adler32(0, null, 0, 0);

    if(length >= (1<<z.istate.wbits)){
      length = (1<<z.istate.wbits)-1;
      index=dictLength - length;
    }
    z.istate.blocks.set_dictionary(dictionary, index, length);
    z.istate.mode = BLOCKS;
    return Z_OK;
  }

//  static private byte[] mark = {(byte)0, (byte)0, (byte)0xff, (byte)0xff};
var mark = [0, 0, 255, 255]

Inflate.prototype.inflateSync = function(z){
    var n;       // number of bytes to look at
    var p;       // pointer to bytes
    var m;       // number of marker bytes found in a row
    var r, w;   // temporaries to save total_in and total_out

    // set up
    if(z == null || z.istate == null)
      return Z_STREAM_ERROR;
    if(z.istate.mode != BAD){
      z.istate.mode = BAD;
      z.istate.marker = 0;
    }
    if((n=z.avail_in)==0)
      return Z_BUF_ERROR;
    p=z.next_in_index;
    m=z.istate.marker;

    // search
    while (n!=0 && m < 4){
      if(z.next_in[p] == mark[m]){
        m++;
      }
      else if(z.next_in[p]!=0){
        m = 0;
      }
      else{
        m = 4 - m;
      }
      p++; n--;
    }

    // restore
    z.total_in += p-z.next_in_index;
    z.next_in_index = p;
    z.avail_in = n;
    z.istate.marker = m;

    // return no joy or set up to restart on a new block
    if(m != 4){
      return Z_DATA_ERROR;
    }
    r=z.total_in;  w=z.total_out;
    this.inflateReset(z);
    z.total_in=r;  z.total_out = w;
    z.istate.mode = BLOCKS;
    return Z_OK;
}

  // Returns true if inflate is currently at the end of a block generated
  // by Z_SYNC_FLUSH or Z_FULL_FLUSH. This function is used by one PPP
  // implementation to provide an additional safety check. PPP uses Z_SYNC_FLUSH
  // but removes the length bytes of the resulting empty stored block. When
  // decompressing, PPP checks that at the end of input packet, inflate is
  // waiting for these length bytes.
Inflate.prototype.inflateSyncPoint = function(z){
    if(z == null || z.istate == null || z.istate.blocks == null)
      return Z_STREAM_ERROR;
    return z.istate.blocks.sync_point();
}


//
// InfBlocks.java
//

var INFBLOCKS_BORDER = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];

function InfBlocks(z, checkfn, w) {
    this.hufts=new Int32Array(MANY*3);
    this.window=new Uint8Array(w);
    this.end=w;
    this.checkfn = checkfn;
    this.mode = IB_TYPE;
    this.reset(z, null);

    this.left = 0;            // if STORED, bytes left to copy

    this.table = 0;           // table lengths (14 bits)
    this.index = 0;           // index into blens (or border)
    this.blens = null;         // bit lengths of codes
    this.bb=new Int32Array(1); // bit length tree depth
    this.tb=new Int32Array(1); // bit length decoding tree

    this.codes = new InfCodes();

    this.last = 0;            // true if this block is the last block

  // mode independent information
    this.bitk = 0;            // bits in bit buffer
    this.bitb = 0;            // bit buffer
    this.read = 0;            // window read pointer
    this.write = 0;           // window write pointer
    this.check = 0;          // check on output

    this.inftree=new InfTree();
}




InfBlocks.prototype.reset = function(z, c){
    if(c) c[0]=this.check;
    if(this.mode==IB_CODES){
      this.codes.free(z);
    }
    this.mode=IB_TYPE;
    this.bitk=0;
    this.bitb=0;
    this.read=this.write=0;

    if(this.checkfn)
      z.adler=this.check=z._adler.adler32(0, null, 0, 0);
  }

 InfBlocks.prototype.proc = function(z, r){
    var t;              // temporary storage
    var b;              // bit buffer
    var k;              // bits in bit buffer
    var p;              // input data pointer
    var n;              // bytes available there
    var q;              // output window write pointer
    var m;              // bytes to end of window or read pointer

    // copy input/output information to locals (UPDATE macro restores)
    {p=z.next_in_index;n=z.avail_in;b=this.bitb;k=this.bitk;}
    {q=this.write;m=(q<this.read ? this.read-q-1 : this.end-q);}

    // process input based on current state
    while(true){
      switch (this.mode){
      case IB_TYPE:

	while(k<(3)){
	  if(n!=0){
	    r=Z_OK;
	  }
	  else{
	    this.bitb=b; this.bitk=k;
	    z.avail_in=n;
	    z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    this.write=q;
	    return this.inflate_flush(z,r);
	  };
	  n--;
	  b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}
	t = (b & 7);
	this.last = t & 1;

	switch (t >>> 1){
        case 0:                         // stored
          {b>>>=(3);k-=(3);}
          t = k & 7;                    // go to byte boundary

          {b>>>=(t);k-=(t);}
          this.mode = IB_LENS;                  // get length of stored block
          break;
        case 1:                         // fixed
          {
              var bl=new Int32Array(1);
	      var bd=new Int32Array(1);
              var tl=[];
	      var td=[];

	      inflate_trees_fixed(bl, bd, tl, td, z);
              this.codes.init(bl[0], bd[0], tl[0], 0, td[0], 0, z);
          }

          {b>>>=(3);k-=(3);}

          this.mode = IB_CODES;
          break;
        case 2:                         // dynamic

          {b>>>=(3);k-=(3);}

          this.mode = IB_TABLE;
          break;
        case 3:                         // illegal

          {b>>>=(3);k-=(3);}
          this.mode = BAD;
          z.msg = "invalid block type";
          r = Z_DATA_ERROR;

	  this.bitb=b; this.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  this.write=q;
	  return this.inflate_flush(z,r);
	}
	break;
      case IB_LENS:
	while(k<(32)){
	  if(n!=0){
	    r=Z_OK;
	  }
	  else{
	    this.bitb=b; this.bitk=k;
	    z.avail_in=n;
	    z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    this.write=q;
	    return this.inflate_flush(z,r);
	  };
	  n--;
	  b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}

	if ((((~b) >>> 16) & 0xffff) != (b & 0xffff)){
	  this.mode = BAD;
	  z.msg = "invalid stored block lengths";
	  r = Z_DATA_ERROR;

	  this.bitb=b; this.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  this.write=q;
	  return this.inflate_flush(z,r);
	}
	this.left = (b & 0xffff);
	b = k = 0;                       // dump bits
	this.mode = this.left!=0 ? IB_STORED : (this.last!=0 ? IB_DRY : IB_TYPE);
	break;
      case IB_STORED:
	if (n == 0){
	  this.bitb=b; this.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  write=q;
	  return this.inflate_flush(z,r);
	}

	if(m==0){
	  if(q==end&&read!=0){
	    q=0; m=(q<this.read ? this.read-q-1 : this.end-q);
	  }
	  if(m==0){
	    this.write=q;
	    r=this.inflate_flush(z,r);
	    q=this.write; m = (q < this.read ? this.read-q-1 : this.end-q);
	    if(q==this.end && this.read != 0){
	      q=0; m = (q < this.read ? this.read-q-1 : this.end-q);
	    }
	    if(m==0){
	      this.bitb=b; this.bitk=k;
	      z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	      this.write=q;
	      return this.inflate_flush(z,r);
	    }
	  }
	}
	r=Z_OK;

	t = this.left;
	if(t>n) t = n;
	if(t>m) t = m;
	arrayCopy(z.next_in, p, this.window, q, t);
	p += t;  n -= t;
	q += t;  m -= t;
	if ((this.left -= t) != 0)
	  break;
	this.mode = (this.last != 0 ? IB_DRY : IB_TYPE);
	break;
      case IB_TABLE:

	while(k<(14)){
	  if(n!=0){
	    r=Z_OK;
	  }
	  else{
	    this.bitb=b; this.bitk=k;
	    z.avail_in=n;
	    z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    this.write=q;
	    return this.inflate_flush(z,r);
	  };
	  n--;
	  b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}

	this.table = t = (b & 0x3fff);
	if ((t & 0x1f) > 29 || ((t >> 5) & 0x1f) > 29)
	  {
	    this.mode = IB_BAD;
	    z.msg = "too many length or distance symbols";
	    r = Z_DATA_ERROR;

	    this.bitb=b; this.bitk=k;
	    z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    this.write=q;
	    return this.inflate_flush(z,r);
	  }
	t = 258 + (t & 0x1f) + ((t >> 5) & 0x1f);
	if(this.blens==null || this.blens.length<t){
	    this.blens=new Int32Array(t);
	}
	else{
	  for(var i=0; i<t; i++){
              this.blens[i]=0;
          }
	}

	{b>>>=(14);k-=(14);}

	this.index = 0;
	mode = IB_BTREE;
      case IB_BTREE:
	while (this.index < 4 + (this.table >>> 10)){
	  while(k<(3)){
	    if(n!=0){
	      r=Z_OK;
	    }
	    else{
	      this.bitb=b; this.bitk=k;
	      z.avail_in=n;
	      z.total_in+=p-z.next_in_index;z.next_in_index=p;
	      this.write=q;
	      return this.inflate_flush(z,r);
	    };
	    n--;
	    b|=(z.next_in[p++]&0xff)<<k;
	    k+=8;
	  }

	  this.blens[INFBLOCKS_BORDER[this.index++]] = b&7;

	  {b>>>=(3);k-=(3);}
	}

	while(this.index < 19){
	  this.blens[INFBLOCKS_BORDER[this.index++]] = 0;
	}

	this.bb[0] = 7;
	t = this.inftree.inflate_trees_bits(this.blens, this.bb, this.tb, this.hufts, z);
	if (t != Z_OK){
	  r = t;
	  if (r == Z_DATA_ERROR){
	    this.blens=null;
	    this.mode = IB_BAD;
	  }

	  this.bitb=b; this.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  write=q;
	  return this.inflate_flush(z,r);
	}

	this.index = 0;
	this.mode = IB_DTREE;
      case IB_DTREE:
	while (true){
	  t = this.table;
	  if(!(this.index < 258 + (t & 0x1f) + ((t >> 5) & 0x1f))){
	    break;
	  }

	  var h; //int[]
	  var i, j, c;

	  t = this.bb[0];

	  while(k<(t)){
	    if(n!=0){
	      r=Z_OK;
	    }
	    else{
	      this.bitb=b; this.bitk=k;
	      z.avail_in=n;
	      z.total_in+=p-z.next_in_index;z.next_in_index=p;
	      this.write=q;
	      return this.inflate_flush(z,r);
	    };
	    n--;
	    b|=(z.next_in[p++]&0xff)<<k;
	    k+=8;
	  }

//	  if (this.tb[0]==-1){
//            dlog("null...");
//	  }

	  t=this.hufts[(this.tb[0]+(b & inflate_mask[t]))*3+1];
	  c=this.hufts[(this.tb[0]+(b & inflate_mask[t]))*3+2];

	  if (c < 16){
	    b>>>=(t);k-=(t);
	    this.blens[this.index++] = c;
	  }
	  else { // c == 16..18
	    i = c == 18 ? 7 : c - 14;
	    j = c == 18 ? 11 : 3;

	    while(k<(t+i)){
	      if(n!=0){
		r=Z_OK;
	      }
	      else{
		this.bitb=b; this.bitk=k;
		z.avail_in=n;
		z.total_in+=p-z.next_in_index;z.next_in_index=p;
		this.write=q;
		return this.inflate_flush(z,r);
	      };
	      n--;
	      b|=(z.next_in[p++]&0xff)<<k;
	      k+=8;
	    }

	    b>>>=(t);k-=(t);

	    j += (b & inflate_mask[i]);

	    b>>>=(i);k-=(i);

	    i = this.index;
	    t = this.table;
	    if (i + j > 258 + (t & 0x1f) + ((t >> 5) & 0x1f) ||
		(c == 16 && i < 1)){
	      this.blens=null;
	      this.mode = IB_BAD;
	      z.msg = "invalid bit length repeat";
	      r = Z_DATA_ERROR;

	      this.bitb=b; this.bitk=k;
	      z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	      this.write=q;
	      return this.inflate_flush(z,r);
	    }

	    c = c == 16 ? this.blens[i-1] : 0;
	    do{
	      this.blens[i++] = c;
	    }
	    while (--j!=0);
	    this.index = i;
	  }
	}

	this.tb[0]=-1;
	{
	    var bl=new Int32Array(1);
	    var bd=new Int32Array(1);
	    var tl=new Int32Array(1);
	    var td=new Int32Array(1);
	    bl[0] = 9;         // must be <= 9 for lookahead assumptions
	    bd[0] = 6;         // must be <= 9 for lookahead assumptions

	    t = this.table;
	    t = this.inftree.inflate_trees_dynamic(257 + (t & 0x1f),
					      1 + ((t >> 5) & 0x1f),
					      this.blens, bl, bd, tl, td, this.hufts, z);

	    if (t != Z_OK){
	        if (t == Z_DATA_ERROR){
	            this.blens=null;
	            this.mode = BAD;
	        }
	        r = t;

	        this.bitb=b; this.bitk=k;
	        z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	        this.write=q;
	        return this.inflate_flush(z,r);
	    }
	    this.codes.init(bl[0], bd[0], this.hufts, tl[0], this.hufts, td[0], z);
	}
	this.mode = IB_CODES;
      case IB_CODES:
	this.bitb=b; this.bitk=k;
	z.avail_in=n; z.total_in+=p-z.next_in_index;z.next_in_index=p;
	this.write=q;

	if ((r = this.codes.proc(this, z, r)) != Z_STREAM_END){
	  return this.inflate_flush(z, r);
	}
	r = Z_OK;
	this.codes.free(z);

	p=z.next_in_index; n=z.avail_in;b=this.bitb;k=this.bitk;
	q=this.write;m = (q < this.read ? this.read-q-1 : this.end-q);

	if (this.last==0){
	  this.mode = IB_TYPE;
	  break;
	}
	this.mode = IB_DRY;
      case IB_DRY:
	this.write=q;
	r = this.inflate_flush(z, r);
	q=this.write; m = (q < this.read ? this.read-q-1 : this.end-q);
	if (this.read != this.write){
	  this.bitb=b; this.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  this.write=q;
	  return this.inflate_flush(z, r);
	}
	mode = DONE;
      case IB_DONE:
	r = Z_STREAM_END;

	this.bitb=b; this.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	this.write=q;
	return this.inflate_flush(z, r);
      case IB_BAD:
	r = Z_DATA_ERROR;

	this.bitb=b; this.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	this.write=q;
	return this.inflate_flush(z, r);

      default:
	r = Z_STREAM_ERROR;

	this.bitb=b; this.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	this.write=q;
	return this.inflate_flush(z, r);
      }
    }
  }

InfBlocks.prototype.free = function(z){
    this.reset(z, null);
    this.window=null;
    this.hufts=null;
}

InfBlocks.prototype.set_dictionary = function(d, start, n){
    arrayCopy(d, start, window, 0, n);
    this.read = this.write = n;
}

  // Returns true if inflate is currently at the end of a block generated
  // by Z_SYNC_FLUSH or Z_FULL_FLUSH.
InfBlocks.prototype.sync_point = function(){
    return this.mode == IB_LENS;
}

  // copy as much as possible from the sliding window to the output area
InfBlocks.prototype.inflate_flush = function(z, r){
    var n;
    var p;
    var q;

    // local copies of source and destination pointers
    p = z.next_out_index;
    q = this.read;

    // compute number of bytes to copy as far as end of window
    n = ((q <= this.write ? this.write : this.end) - q);
    if (n > z.avail_out) n = z.avail_out;
    if (n!=0 && r == Z_BUF_ERROR) r = Z_OK;

    // update counters
    z.avail_out -= n;
    z.total_out += n;

    // update check information
    if(this.checkfn != null)
      z.adler=this.check=z._adler.adler32(this.check, this.window, q, n);

    // copy as far as end of window
    arrayCopy(this.window, q, z.next_out, p, n);
    p += n;
    q += n;

    // see if more to copy at beginning of window
    if (q == this.end){
      // wrap pointers
      q = 0;
      if (this.write == this.end)
        this.write = 0;

      // compute bytes to copy
      n = this.write - q;
      if (n > z.avail_out) n = z.avail_out;
      if (n!=0 && r == Z_BUF_ERROR) r = Z_OK;

      // update counters
      z.avail_out -= n;
      z.total_out += n;

      // update check information
      if(this.checkfn != null)
	z.adler=this.check=z._adler.adler32(this.check, this.window, q, n);

      // copy
      arrayCopy(this.window, q, z.next_out, p, n);
      p += n;
      q += n;
    }

    // update pointers
    z.next_out_index = p;
    this.read = q;

    // done
    return r;
  }

//
// InfCodes.java
//

var IC_START=0;  // x: set up for LEN
var IC_LEN=1;    // i: get length/literal/eob next
var IC_LENEXT=2; // i: getting length extra (have base)
var IC_DIST=3;   // i: get distance next
var IC_DISTEXT=4;// i: getting distance extra
var IC_COPY=5;   // o: copying bytes in window, waiting for space
var IC_LIT=6;    // o: got literal, waiting for output space
var IC_WASH=7;   // o: got eob, possibly still output waiting
var IC_END=8;    // x: got eob and all data flushed
var IC_BADCODE=9;// x: got error

function InfCodes() {
}

InfCodes.prototype.init = function(bl, bd, tl, tl_index, td, td_index, z) {
    this.mode=IC_START;
    this.lbits=bl;
    this.dbits=bd;
    this.ltree=tl;
    this.ltree_index=tl_index;
    this.dtree = td;
    this.dtree_index=td_index;
    this.tree=null;
}

InfCodes.prototype.proc = function(s, z, r){
    var j;              // temporary storage
    var t;              // temporary pointer (int[])
    var tindex;         // temporary pointer
    var e;              // extra bits or operation
    var b=0;            // bit buffer
    var k=0;            // bits in bit buffer
    var p=0;            // input data pointer
    var n;              // bytes available there
    var q;              // output window write pointer
    var m;              // bytes to end of window or read pointer
    var f;              // pointer to copy strings from

    // copy input/output information to locals (UPDATE macro restores)
    p=z.next_in_index;n=z.avail_in;b=s.bitb;k=s.bitk;
    q=s.write;m=q<s.read?s.read-q-1:s.end-q;

    // process input and output based on current state
    while (true){
      switch (this.mode){
	// waiting for "i:"=input, "o:"=output, "x:"=nothing
      case IC_START:         // x: set up for LEN
	if (m >= 258 && n >= 10){

	  s.bitb=b;s.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  s.write=q;
	  r = this.inflate_fast(this.lbits, this.dbits,
			   this.ltree, this.ltree_index,
			   this.dtree, this.dtree_index,
			   s, z);

	  p=z.next_in_index;n=z.avail_in;b=s.bitb;k=s.bitk;
	  q=s.write;m=q<s.read?s.read-q-1:s.end-q;

	  if (r != Z_OK){
	    this.mode = r == Z_STREAM_END ? IC_WASH : IC_BADCODE;
	    break;
	  }
	}
	this.need = this.lbits;
	this.tree = this.ltree;
	this.tree_index=this.ltree_index;

	this.mode = IC_LEN;
      case IC_LEN:           // i: get length/literal/eob next
	j = this.need;

	while(k<(j)){
	  if(n!=0)r=Z_OK;
	  else{

	    s.bitb=b;s.bitk=k;
	    z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    s.write=q;
	    return s.inflate_flush(z,r);
	  }
	  n--;
	  b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}

	tindex=(this.tree_index+(b&inflate_mask[j]))*3;

	b>>>=(this.tree[tindex+1]);
	k-=(this.tree[tindex+1]);

	e=this.tree[tindex];

	if(e == 0){               // literal
	  this.lit = this.tree[tindex+2];
	  this.mode = IC_LIT;
	  break;
	}
	if((e & 16)!=0 ){          // length
	  this.get = e & 15;
	  this.len = this.tree[tindex+2];
	  this.mode = IC_LENEXT;
	  break;
	}
	if ((e & 64) == 0){        // next table
	  this.need = e;
	  this.tree_index = tindex/3 + this.tree[tindex+2];
	  break;
	}
	if ((e & 32)!=0){               // end of block
	  this.mode = IC_WASH;
	  break;
	}
	this.mode = IC_BADCODE;        // invalid code
	z.msg = "invalid literal/length code";
	r = Z_DATA_ERROR;

	s.bitb=b;s.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	s.write=q;
	return s.inflate_flush(z,r);

      case IC_LENEXT:        // i: getting length extra (have base)
	j = this.get;

	while(k<(j)){
	  if(n!=0)r=Z_OK;
	  else{

	    s.bitb=b;s.bitk=k;
	    z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    s.write=q;
	    return s.inflate_flush(z,r);
	  }
	  n--; b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}

	this.len += (b & inflate_mask[j]);

	b>>=j;
	k-=j;

	this.need = this.dbits;
	this.tree = this.dtree;
	this.tree_index = this.dtree_index;
	this.mode = IC_DIST;
      case IC_DIST:          // i: get distance next
	j = this.need;

	while(k<(j)){
	  if(n!=0)r=Z_OK;
	  else{

	    s.bitb=b;s.bitk=k;
	    z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    s.write=q;
	    return s.inflate_flush(z,r);
	  }
	  n--; b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}

	tindex=(this.tree_index+(b & inflate_mask[j]))*3;

	b>>=this.tree[tindex+1];
	k-=this.tree[tindex+1];

	e = (this.tree[tindex]);
	if((e & 16)!=0){               // distance
	  this.get = e & 15;
	  this.dist = this.tree[tindex+2];
	  this.mode = IC_DISTEXT;
	  break;
	}
	if ((e & 64) == 0){        // next table
	  this.need = e;
	  this.tree_index = tindex/3 + this.tree[tindex+2];
	  break;
	}
	this.mode = IC_BADCODE;        // invalid code
	z.msg = "invalid distance code";
	r = Z_DATA_ERROR;

	s.bitb=b;s.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	s.write=q;
	return s.inflate_flush(z,r);

      case IC_DISTEXT:       // i: getting distance extra
	j = this.get;

	while(k<(j)){
	  if(n!=0)r=Z_OK;
	  else{

	    s.bitb=b;s.bitk=k;
	    z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	    s.write=q;
	    return s.inflate_flush(z,r);
	  }
	  n--; b|=(z.next_in[p++]&0xff)<<k;
	  k+=8;
	}

	this.dist += (b & inflate_mask[j]);

	b>>=j;
	k-=j;

	this.mode = IC_COPY;
      case IC_COPY:          // o: copying bytes in window, waiting for space
        f = q - this.dist;
        while(f < 0){     // modulo window size-"while" instead
          f += s.end;     // of "if" handles invalid distances
	}
	while (this.len!=0){

	  if(m==0){
	    if(q==s.end&&s.read!=0){q=0;m=q<s.read?s.read-q-1:s.end-q;}
	    if(m==0){
	      s.write=q; r=s.inflate_flush(z,r);
	      q=s.write;m=q<s.read?s.read-q-1:s.end-q;

	      if(q==s.end&&s.read!=0){q=0;m=q<s.read?s.read-q-1:s.end-q;}

	      if(m==0){
		s.bitb=b;s.bitk=k;
		z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
		s.write=q;
		return s.inflate_flush(z,r);
	      }
	    }
	  }

	  s.window[q++]=s.window[f++]; m--;

	  if (f == s.end)
            f = 0;
	  this.len--;
	}
	this.mode = IC_START;
	break;
      case IC_LIT:           // o: got literal, waiting for output space
	if(m==0){
	  if(q==s.end&&s.read!=0){q=0;m=q<s.read?s.read-q-1:s.end-q;}
	  if(m==0){
	    s.write=q; r=s.inflate_flush(z,r);
	    q=s.write;m=q<s.read?s.read-q-1:s.end-q;

	    if(q==s.end&&s.read!=0){q=0;m=q<s.read?s.read-q-1:s.end-q;}
	    if(m==0){
	      s.bitb=b;s.bitk=k;
	      z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	      s.write=q;
	      return s.inflate_flush(z,r);
	    }
	  }
	}
	r=Z_OK;

	s.window[q++]=this.lit; m--;

	this.mode = IC_START;
	break;
      case IC_WASH:           // o: got eob, possibly more output
	if (k > 7){        // return unused byte, if any
	  k -= 8;
	  n++;
	  p--;             // can always return one
	}

	s.write=q; r=s.inflate_flush(z,r);
	q=s.write;m=q<s.read?s.read-q-1:s.end-q;

	if (s.read != s.write){
	  s.bitb=b;s.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  s.write=q;
	  return s.inflate_flush(z,r);
	}
	this.mode = IC_END;
      case IC_END:
	r = Z_STREAM_END;
	s.bitb=b;s.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	s.write=q;
	return s.inflate_flush(z,r);

      case IC_BADCODE:       // x: got error

	r = Z_DATA_ERROR;

	s.bitb=b;s.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	s.write=q;
	return s.inflate_flush(z,r);

      default:
	r = Z_STREAM_ERROR;

	s.bitb=b;s.bitk=k;
	z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	s.write=q;
	return s.inflate_flush(z,r);
      }
    }
  }

InfCodes.prototype.free = function(z){
    //  ZFREE(z, c);
}

  // Called with number of bytes left to write in window at least 258
  // (the maximum string length) and number of input bytes available
  // at least ten.  The ten bytes are six bytes for the longest length/
  // distance pair plus four bytes for overloading the bit buffer.

InfCodes.prototype.inflate_fast = function(bl, bd, tl, tl_index, td, td_index, s, z) {
    var t;                // temporary pointer
    var   tp;             // temporary pointer (int[])
    var tp_index;         // temporary pointer
    var e;                // extra bits or operation
    var b;                // bit buffer
    var k;                // bits in bit buffer
    var p;                // input data pointer
    var n;                // bytes available there
    var q;                // output window write pointer
    var m;                // bytes to end of window or read pointer
    var ml;               // mask for literal/length tree
    var md;               // mask for distance tree
    var c;                // bytes to copy
    var d;                // distance back to copy from
    var r;                // copy source pointer

    var tp_index_t_3;     // (tp_index+t)*3

    // load input, output, bit values
    p=z.next_in_index;n=z.avail_in;b=s.bitb;k=s.bitk;
    q=s.write;m=q<s.read?s.read-q-1:s.end-q;

    // initialize masks
    ml = inflate_mask[bl];
    md = inflate_mask[bd];

    // do until not enough input or output space for fast loop
    do {                          // assume called with m >= 258 && n >= 10
      // get literal/length code
      while(k<(20)){              // max bits for literal/length code
	n--;
	b|=(z.next_in[p++]&0xff)<<k;k+=8;
      }

      t= b&ml;
      tp=tl;
      tp_index=tl_index;
      tp_index_t_3=(tp_index+t)*3;
      if ((e = tp[tp_index_t_3]) == 0){
	b>>=(tp[tp_index_t_3+1]); k-=(tp[tp_index_t_3+1]);

	s.window[q++] = tp[tp_index_t_3+2];
	m--;
	continue;
      }
      do {

	b>>=(tp[tp_index_t_3+1]); k-=(tp[tp_index_t_3+1]);

	if((e&16)!=0){
	  e &= 15;
	  c = tp[tp_index_t_3+2] + (b & inflate_mask[e]);

	  b>>=e; k-=e;

	  // decode distance base of block to copy
	  while(k<(15)){           // max bits for distance code
	    n--;
	    b|=(z.next_in[p++]&0xff)<<k;k+=8;
	  }

	  t= b&md;
	  tp=td;
	  tp_index=td_index;
          tp_index_t_3=(tp_index+t)*3;
	  e = tp[tp_index_t_3];

	  do {

	    b>>=(tp[tp_index_t_3+1]); k-=(tp[tp_index_t_3+1]);

	    if((e&16)!=0){
	      // get extra bits to add to distance base
	      e &= 15;
	      while(k<(e)){         // get extra bits (up to 13)
		n--;
		b|=(z.next_in[p++]&0xff)<<k;k+=8;
	      }

	      d = tp[tp_index_t_3+2] + (b&inflate_mask[e]);

	      b>>=(e); k-=(e);

	      // do the copy
	      m -= c;
	      if (q >= d){                // offset before dest
		//  just copy
		r=q-d;
		if(q-r>0 && 2>(q-r)){
		  s.window[q++]=s.window[r++]; // minimum count is three,
		  s.window[q++]=s.window[r++]; // so unroll loop a little
		  c-=2;
		}
		else{
		  s.window[q++]=s.window[r++]; // minimum count is three,
		  s.window[q++]=s.window[r++]; // so unroll loop a little
		  c-=2;
		}
	      }
	      else{                  // else offset after destination
                r=q-d;
                do{
                  r+=s.end;          // force pointer in window
                }while(r<0);         // covers invalid distances
		e=s.end-r;
		if(c>e){             // if source crosses,
		  c-=e;              // wrapped copy
		  if(q-r>0 && e>(q-r)){
		    do{s.window[q++] = s.window[r++];}
		    while(--e!=0);
		  }
		  else{
		    arrayCopy(s.window, r, s.window, q, e);
		    q+=e; r+=e; e=0;
		  }
		  r = 0;                  // copy rest from start of window
		}

	      }

	      // copy all or what's left
              do{s.window[q++] = s.window[r++];}
		while(--c!=0);
	      break;
	    }
	    else if((e&64)==0){
	      t+=tp[tp_index_t_3+2];
	      t+=(b&inflate_mask[e]);
	      tp_index_t_3=(tp_index+t)*3;
	      e=tp[tp_index_t_3];
	    }
	    else{
	      z.msg = "invalid distance code";

	      c=z.avail_in-n;c=(k>>3)<c?k>>3:c;n+=c;p-=c;k-=c<<3;

	      s.bitb=b;s.bitk=k;
	      z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	      s.write=q;

	      return Z_DATA_ERROR;
	    }
	  }
	  while(true);
	  break;
	}

	if((e&64)==0){
	  t+=tp[tp_index_t_3+2];
	  t+=(b&inflate_mask[e]);
	  tp_index_t_3=(tp_index+t)*3;
	  if((e=tp[tp_index_t_3])==0){

	    b>>=(tp[tp_index_t_3+1]); k-=(tp[tp_index_t_3+1]);

	    s.window[q++]=tp[tp_index_t_3+2];
	    m--;
	    break;
	  }
	}
	else if((e&32)!=0){

	  c=z.avail_in-n;c=(k>>3)<c?k>>3:c;n+=c;p-=c;k-=c<<3;

	  s.bitb=b;s.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  s.write=q;

	  return Z_STREAM_END;
	}
	else{
	  z.msg="invalid literal/length code";

	  c=z.avail_in-n;c=(k>>3)<c?k>>3:c;n+=c;p-=c;k-=c<<3;

	  s.bitb=b;s.bitk=k;
	  z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
	  s.write=q;

	  return Z_DATA_ERROR;
	}
      }
      while(true);
    }
    while(m>=258 && n>= 10);

    // not enough input or output--restore pointers and return
    c=z.avail_in-n;c=(k>>3)<c?k>>3:c;n+=c;p-=c;k-=c<<3;

    s.bitb=b;s.bitk=k;
    z.avail_in=n;z.total_in+=p-z.next_in_index;z.next_in_index=p;
    s.write=q;

    return Z_OK;
}

//
// InfTree.java
//

function InfTree() {
}

InfTree.prototype.huft_build = function(b, bindex, n, s, d, e, t, m, hp, hn, v) {

    // Given a list of code lengths and a maximum table size, make a set of
    // tables to decode that set of codes.  Return Z_OK on success, Z_BUF_ERROR
    // if the given code set is incomplete (the tables are still built in this
    // case), Z_DATA_ERROR if the input is invalid (an over-subscribed set of
    // lengths), or Z_MEM_ERROR if not enough memory.

    var a;                       // counter for codes of length k
    var f;                       // i repeats in table every f entries
    var g;                       // maximum code length
    var h;                       // table level
    var i;                       // counter, current code
    var j;                       // counter
    var k;                       // number of bits in current code
    var l;                       // bits per table (returned in m)
    var mask;                    // (1 << w) - 1, to avoid cc -O bug on HP
    var p;                       // pointer into c[], b[], or v[]
    var q;                       // points to current table
    var w;                       // bits before this table == (l * h)
    var xp;                      // pointer into x
    var y;                       // number of dummy codes added
    var z;                       // number of entries in current table

    // Generate counts for each bit length

    p = 0; i = n;
    do {
      this.c[b[bindex+p]]++; p++; i--;   // assume all entries <= BMAX
    }while(i!=0);

    if(this.c[0] == n){                // null input--all zero length codes
      t[0] = -1;
      m[0] = 0;
      return Z_OK;
    }

    // Find minimum and maximum length, bound *m by those
    l = m[0];
    for (j = 1; j <= BMAX; j++)
      if(this.c[j]!=0) break;
    k = j;                        // minimum code length
    if(l < j){
      l = j;
    }
    for (i = BMAX; i!=0; i--){
      if(this.c[i]!=0) break;
    }
    g = i;                        // maximum code length
    if(l > i){
      l = i;
    }
    m[0] = l;

    // Adjust last length count to fill out codes, if needed
    for (y = 1 << j; j < i; j++, y <<= 1){
      if ((y -= this.c[j]) < 0){
        return Z_DATA_ERROR;
      }
    }
    if ((y -= this.c[i]) < 0){
      return Z_DATA_ERROR;
    }
    this.c[i] += y;

    // Generate starting offsets into the value table for each length
    this.x[1] = j = 0;
    p = 1;  xp = 2;
    while (--i!=0) {                 // note that i == g from above
      this.x[xp] = (j += this.c[p]);
      xp++;
      p++;
    }

    // Make a table of values in order of bit lengths
    i = 0; p = 0;
    do {
      if ((j = b[bindex+p]) != 0){
        this.v[this.x[j]++] = i;
      }
      p++;
    }
    while (++i < n);
    n = this.x[g];                     // set n to length of v

    // Generate the Huffman codes and for each, make the table entries
    this.x[0] = i = 0;                 // first Huffman code is zero
    p = 0;                        // grab values in bit order
    h = -1;                       // no tables yet--level -1
    w = -l;                       // bits decoded == (l * h)
    this.u[0] = 0;                     // just to keep compilers happy
    q = 0;                        // ditto
    z = 0;                        // ditto

    // go through the bit lengths (k already is bits in shortest code)
    for (; k <= g; k++){
      a = this.c[k];
      while (a--!=0){
	// here i is the Huffman code of length k bits for value *p
	// make tables up to required level
        while (k > w + l){
          h++;
          w += l;                 // previous table always l bits
	  // compute minimum size table less than or equal to l bits
          z = g - w;
          z = (z > l) ? l : z;        // table size upper limit
          if((f=1<<(j=k-w))>a+1){     // try a k-w bit table
                                      // too few codes for k-w bit table
            f -= a + 1;               // deduct codes from patterns left
            xp = k;
            if(j < z){
              while (++j < z){        // try smaller tables up to z bits
                if((f <<= 1) <= this.c[++xp])
                  break;              // enough codes to use up j bits
                f -= this.c[xp];           // else deduct codes from patterns
              }
	    }
          }
          z = 1 << j;                 // table entries for j-bit table

	  // allocate new table
          if (this.hn[0] + z > MANY){       // (note: doesn't matter for fixed)
            return Z_DATA_ERROR;       // overflow of MANY
          }
          this.u[h] = q = /*hp+*/ this.hn[0];   // DEBUG
          this.hn[0] += z;

	  // connect to last table, if there is one
	  if(h!=0){
            this.x[h]=i;           // save pattern for backing up
            this.r[0]=j;     // bits in this table
            this.r[1]=l;     // bits to dump before this table
            j=i>>>(w - l);
            this.r[2] = (q - this.u[h-1] - j);               // offset to this table
            arrayCopy(this.r, 0, hp, (this.u[h-1]+j)*3, 3); // connect to last table
          }
          else{
            t[0] = q;               // first table is returned result
	  }
        }

	// set up table entry in r
        this.r[1] = (k - w);
        if (p >= n){
          this.r[0] = 128 + 64;      // out of values--invalid code
	}
        else if (v[p] < s){
          this.r[0] = (this.v[p] < 256 ? 0 : 32 + 64);  // 256 is end-of-block
          this.r[2] = this.v[p++];          // simple code is just the value
        }
        else{
          this.r[0]=(e[this.v[p]-s]+16+64); // non-simple--look up in lists
          this.r[2]=d[this.v[p++] - s];
        }

        // fill code-like entries with r
        f=1<<(k-w);
        for (j=i>>>w;j<z;j+=f){
          arrayCopy(this.r, 0, hp, (q+j)*3, 3);
	}

	// backwards increment the k-bit code i
        for (j = 1 << (k - 1); (i & j)!=0; j >>>= 1){
          i ^= j;
	}
        i ^= j;

	// backup over finished tables
        mask = (1 << w) - 1;      // needed on HP, cc -O bug
        while ((i & mask) != this.x[h]){
          h--;                    // don't need to update q
          w -= l;
          mask = (1 << w) - 1;
        }
      }
    }
    // Return Z_BUF_ERROR if we were given an incomplete table
    return y != 0 && g != 1 ? Z_BUF_ERROR : Z_OK;
}

InfTree.prototype.inflate_trees_bits = function(c, bb, tb, hp, z) {
    var result;
    this.initWorkArea(19);
    this.hn[0]=0;
    result = this.huft_build(c, 0, 19, 19, null, null, tb, bb, hp, this.hn, this.v);

    if(result == Z_DATA_ERROR){
      z.msg = "oversubscribed dynamic bit lengths tree";
    }
    else if(result == Z_BUF_ERROR || bb[0] == 0){
      z.msg = "incomplete dynamic bit lengths tree";
      result = Z_DATA_ERROR;
    }
    return result;
}

InfTree.prototype.inflate_trees_dynamic = function(nl, nd, c, bl, bd, tl, td, hp, z) {
    var result;

    // build literal/length tree
    this.initWorkArea(288);
    this.hn[0]=0;
    result = this.huft_build(c, 0, nl, 257, cplens, cplext, tl, bl, hp, this.hn, this.v);
    if (result != Z_OK || bl[0] == 0){
      if(result == Z_DATA_ERROR){
        z.msg = "oversubscribed literal/length tree";
      }
      else if (result != Z_MEM_ERROR){
        z.msg = "incomplete literal/length tree";
        result = Z_DATA_ERROR;
      }
      return result;
    }

    // build distance tree
    this.initWorkArea(288);
    result = this.huft_build(c, nl, nd, 0, cpdist, cpdext, td, bd, hp, this.hn, this.v);

    if (result != Z_OK || (bd[0] == 0 && nl > 257)){
      if (result == Z_DATA_ERROR){
        z.msg = "oversubscribed distance tree";
      }
      else if (result == Z_BUF_ERROR) {
        z.msg = "incomplete distance tree";
        result = Z_DATA_ERROR;
      }
      else if (result != Z_MEM_ERROR){
        z.msg = "empty distance tree with lengths";
        result = Z_DATA_ERROR;
      }
      return result;
    }

    return Z_OK;
}
/*
  static int inflate_trees_fixed(int[] bl,  //literal desired/actual bit depth
                                 int[] bd,  //distance desired/actual bit depth
                                 int[][] tl,//literal/length tree result
                                 int[][] td,//distance tree result
                                 ZStream z  //for memory allocation
				 ){

*/

function inflate_trees_fixed(bl, bd, tl, td, z) {
    bl[0]=fixed_bl;
    bd[0]=fixed_bd;
    tl[0]=fixed_tl;
    td[0]=fixed_td;
    return Z_OK;
}

InfTree.prototype.initWorkArea = function(vsize){
    if(this.hn==null){
        this.hn=new Int32Array(1);
        this.v=new Int32Array(vsize);
        this.c=new Int32Array(BMAX+1);
        this.r=new Int32Array(3);
        this.u=new Int32Array(BMAX);
        this.x=new Int32Array(BMAX+1);
    }
    if(this.v.length<vsize){
        this.v=new Int32Array(vsize);
    }
    for(var i=0; i<vsize; i++){this.v[i]=0;}
    for(var i=0; i<BMAX+1; i++){this.c[i]=0;}
    for(var i=0; i<3; i++){this.r[i]=0;}
//  for(int i=0; i<BMAX; i++){u[i]=0;}
    arrayCopy(this.c, 0, this.u, 0, BMAX);
//  for(int i=0; i<BMAX+1; i++){x[i]=0;}
    arrayCopy(this.c, 0, this.x, 0, BMAX+1);
}

var testArray = new Uint8Array(1);
var hasSubarray = (typeof testArray.subarray === 'function');
var hasSlice = false; /* (typeof testArray.slice === 'function'); */ // Chrome slice performance is so dire that we're currently not using it...

function arrayCopy(src, srcOffset, dest, destOffset, count) {
    if (count == 0) {
        return;
    }
    if (!src) {
        throw "Undef src";
    } else if (!dest) {
        throw "Undef dest";
    }

    if (srcOffset == 0 && count == src.length) {
        arrayCopy_fast(src, dest, destOffset);
    } else if (hasSubarray) {
        arrayCopy_fast(src.subarray(srcOffset, srcOffset + count), dest, destOffset);
    } else if (src.BYTES_PER_ELEMENT == 1 && count > 100) {
        arrayCopy_fast(new Uint8Array(src.buffer, src.byteOffset + srcOffset, count), dest, destOffset);
    } else {
        arrayCopy_slow(src, srcOffset, dest, destOffset, count);
    }

}

function arrayCopy_slow(src, srcOffset, dest, destOffset, count) {

    // dlog('_slow call: srcOffset=' + srcOffset + '; destOffset=' + destOffset + '; count=' + count);

     for (var i = 0; i < count; ++i) {
        dest[destOffset + i] = src[srcOffset + i];
    }
}

function arrayCopy_fast(src, dest, destOffset) {
    dest.set(src, destOffset);
}


  // largest prime smaller than 65536
var ADLER_BASE=65521;
  // NMAX is the largest n such that 255n(n+1)/2 + (n+1)(BASE-1) <= 2^32-1
var ADLER_NMAX=5552;

function adler32(adler, /* byte[] */ buf,  index, len){
    if(buf == null){ return 1; }

    var s1=adler&0xffff;
    var s2=(adler>>16)&0xffff;
    var k;

    while(len > 0) {
      k=len<ADLER_NMAX?len:ADLER_NMAX;
      len-=k;
      while(k>=16){
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        s1+=buf[index++]&0xff; s2+=s1;
        k-=16;
      }
      if(k!=0){
        do{
          s1+=buf[index++]&0xff; s2+=s1;
        }
        while(--k!=0);
      }
      s1%=ADLER_BASE;
      s2%=ADLER_BASE;
    }
    return (s2<<16)|s1;
}



function jszlib_inflate_buffer(buffer, start, length, afterUncOffset) {
    if (!start) {
        buffer = new Uint8Array(buffer);
    } else if (!length) {
        buffer = new Uint8Array(buffer, start, buffer.byteLength - start);
    } else {
        buffer = new Uint8Array(buffer, start, length);
    }

    var z = new ZStream();
    z.inflateInit(DEF_WBITS, true);
    z.next_in = buffer;
    z.next_in_index = 0;
    z.avail_in = buffer.length;

    var oBlockList = [];
    var totalSize = 0;
    while (true) {
        var obuf = new Uint8Array(32000);
        z.next_out = obuf;
        z.next_out_index = 0;
        z.avail_out = obuf.length;
        var status = z.inflate(Z_NO_FLUSH);
        if (status != Z_OK && status != Z_STREAM_END && status != Z_BUF_ERROR) {
            throw z.msg;
        }
        if (z.avail_out != 0) {
            var newob = new Uint8Array(obuf.length - z.avail_out);
            arrayCopy(obuf, 0, newob, 0, (obuf.length - z.avail_out));
            obuf = newob;
        }
        oBlockList.push(obuf);
        totalSize += obuf.length;
        if (status == Z_STREAM_END || status == Z_BUF_ERROR) {
            break;
        }
    }

    if (afterUncOffset) {
        afterUncOffset[0] = (start || 0) + z.next_in_index;
    }

    if (oBlockList.length == 1) {
        return oBlockList[0].buffer;
    } else {
        var out = new Uint8Array(totalSize);
        var cursor = 0;
        for (var i = 0; i < oBlockList.length; ++i) {
            var b = oBlockList[i];
            arrayCopy(b, 0, out, cursor, b.length);
            cursor += b.length;
        }
        return out.buffer;
    }
}

return {
    inflateBuffer: jszlib_inflate_buffer,
    arrayCopy: arrayCopy
  };
});
