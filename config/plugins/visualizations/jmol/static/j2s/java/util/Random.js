(function(){
var c$ = Clazz.decorateAsClass(function(){
this.haveNextNextGaussian = false;
this.seed = 0;
this.nextNextGaussian = 0;
Clazz.instantialize(this, arguments);}, java.util, "Random", null, java.io.Serializable);
Clazz.makeConstructor(c$, 
function(){
var seed = -2147483648;
{
arguments.length == 1 && (seed = arguments[0]);
}if (seed == -2147483648) seed = System.currentTimeMillis();
this.setSeed(seed);
});
Clazz.defineMethod(c$, "next", 
function(bits){
this.seed = (this.seed * 25214903917 + 0xb) & (281474976710655);
return (this.seed >>> (48 - bits));
}, "~N");
Clazz.defineMethod(c$, "nextBoolean", 
function(){
{
return Math.random () > 0.5;
}});
Clazz.defineMethod(c$, "nextBytes", 
function(buf){
{
var rand = 0;
var count = 0;
var loop = 0;
while (count < buf.length) {
if (loop == 0) {
rand = this.nextInt();
loop = 3;
} else {
loop--;
}buf[count++] = rand;
rand >>= 8;
}
}}, "~A");
Clazz.defineMethod(c$, "nextDouble", 
function(){
{
return Math.random ();
}});
Clazz.defineMethod(c$, "nextFloat", 
function(){
{
return Math.random ();
}});
Clazz.defineMethod(c$, "nextGaussian", 
function(){
if (this.haveNextNextGaussian) {
this.haveNextNextGaussian = false;
return this.nextNextGaussian;
}var v1;
var v2;
var s;
do {
v1 = 2 * this.nextDouble() - 1;
v2 = 2 * this.nextDouble() - 1;
s = v1 * v1 + v2 * v2;
} while (s >= 1);
var norm = Math.sqrt(-2 * Math.log(s) / s);
this.nextNextGaussian = v2 * norm;
this.haveNextNextGaussian = true;
return v1 * norm;
});
Clazz.defineMethod(c$, "nextInt", 
function(n){
{
if (arguments.length == 0)
return Math.random()*0x100000000 | 0;
}if (n <= 0) {
throw  new IllegalArgumentException();
}{
return Math.random() * n|0
}}, "~N");
Clazz.defineMethod(c$, "nextLong", 
function(){
return (this.next(32) << 32) + this.next(32);
});
Clazz.defineMethod(c$, "setSeed", 
function(seed){
{
Math.seedrandom(seed);
}}, "~N");
{
{
(function (pool, math, width, chunks, significance, overflow, startdenom) {
var copyright = "Copyright 2010 David Bau, all rights reserved. (BSD)"
//
// seedrandom()
// This is the seedrandom function described above.
//
math['seedrandom'] = function seedrandom(seed, use_entropy) {
var key = [];
var arc4;
// Flatten the seed string or build one from local entropy if needed.
seed = mixkey(flatten(
use_entropy ? [seed, pool] :
arguments.length ? seed :
[new Date().getTime(), pool, window], 3), key);
// Use the seed to initialize an ARC4 generator.
arc4 = new ARC4(key);
// Mix the randomness into accumulated entropy.
mixkey(arc4.S, pool);
// Override Math.random
// This function returns a random double in [0, 1) that contains
// randomness in every bit of the mantissa of the IEEE 754 value.
math['random'] = function random() {  // Closure to return a random double:
var n = arc4.g(chunks);             // Start with a numerator n < 2 ^ 48
var d = startdenom;                 //   and denominator d = 2 ^ 48.
var x = 0;                          //   and no 'extra last byte'.
while (n < significance) {          // Fill up all significant digits by
n = (n + x) * width;              //   shifting numerator and
d *= width;                       //   denominator and generating a
x = arc4.g(1);                    //   new least-significant-byte.
}
while (n >= overflow) {             // To avoid rounding up, before adding
n /= 2;                           //   last byte, shift everything
d /= 2;                           //   right using integer math until
x >>>= 1;                         //   we have exactly the desired bits.
}
return (n + x) / d;                 // Form the number within [0, 1).
};
// Return the seed that was used
return seed;
};
//
// ARC4
//
// An ARC4 implementation.  The constructor takes a key in the form of
// an array of at most (width) integers that should be 0 <= x < (width).
//
// The g(count) method returns a pseudorandom integer that concatenates
// the next (count) outputs from ARC4.  Its return value is a number x
// that is in the range 0 <= x < (width ^ count).
//
function ARC4(key) {
var t, u, me = this, keylen = key.length;
var i = 0, j = me.i = me.j = me.m = 0;
me.S = [];
me.c = [];
// The empty key [] is treated as [0].
if (!keylen) { key = [keylen++]; }
// Set up S using the standard key scheduling algorithm.
while (i < width) { me.S[i] = i++; }
for (i = 0; i < width; i++) {
t = me.S[i];
j = lowbits(j + t + key[i % keylen]);
u = me.S[j];
me.S[i] = u;
me.S[j] = t;
}
// The "g" method returns the next (count) outputs as one number.
me.g = function getnext(count) {
var s = me.S;
var i = lowbits(me.i + 1); var t = s[i];
var j = lowbits(me.j + t); var u = s[j];
s[i] = u;
s[j] = t;
var r = s[lowbits(t + u)];
while (--count) {
i = lowbits(i + 1); t = s[i];
j = lowbits(j + t); u = s[j];
s[i] = u;
s[j] = t;
r = r * width + s[lowbits(t + u)];
}
me.i = i;
me.j = j;
return r;
};
// For robust unpredictability discard an initial batch of values.
// See http://www.rsa.com/rsalabs/node.asp?id=2009
me.g(width);
}
//
// flatten()
// Converts an object tree to nested arrays of strings.
//
function flatten(obj, depth, result, prop) {
result = [];
if (depth && typeof(obj) == 'object') {
for (prop in obj) {
if (prop.indexOf('S') < 5) {    // Avoid FF3 bug (local/sessionStorage)
try { result.push(flatten(obj[prop], depth - 1)); } catch (e) {}
}
}
}
return result.length ? result : '' + obj;
}
//
// mixkey()
// Mixes a string seed into a key that is an array of integers, and
// returns a shortened string seed that is equivalent to the result key.
//
function mixkey(seed, key, smear, j) {
seed += '';                         // Ensure the seed is a string
smear = 0;
for (j = 0; j < seed.length; j++) {
key[lowbits(j)] =
lowbits((smear ^= key[lowbits(j)] * 19) + seed.charCodeAt(j));
}
seed = '';
for (j in key) { seed += String.fromCharCode(key[j]); }
return seed;
}
//
// lowbits()
// A quick "n mod width" for width a power of 2.
//
function lowbits(n) { return n & (width - 1); }
//
// The following constants are related to IEEE 754 limits.
//
startdenom = math.pow(width, chunks);
significance = math.pow(2, significance);
overflow = significance * 2;
//
// When seedrandom.js is loaded, we immediately mix a few bits
// from the built-in RNG into the entropy pool.  Because we do
// not want to intefere with determinstic PRNG state later,
// seedrandom will not call math.random on its own again after
// initialization.
//
mixkey(math.random(), pool);
// End anonymous scope, and pass initial values.
})(
[],   // pool: entropy pool starts empty
Math, // math: package containing random, pow, and seedrandom
256,  // width: each RC4 output is 0 <= x < 256
6,    // chunks: at least six RC4 outputs for each double
52    // significance: there are 52 significant digits in a double
);
}}})();
;//5.0.1-v2 Sat Apr 06 02:44:31 CDT 2024
