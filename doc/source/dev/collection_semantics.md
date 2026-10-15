# Collection Semantics

This document describes the semantics around working with Galaxy dataset collections.
In particular it describes how they operate within Galaxy tools and workflows.

:::{admonition} You Probably Don't Need to Read This
:class: caution

Any significantly sophisticated workflow language will have ways to collect data
into arrays or vectors or dictionaries and apply operations across this data (mapping)
or reduce the dimensionality of this data (reductions). Typically, this is explicitly
annotated with map functions or for loops. Galaxy however is designed to be a point
and click interface for connecting steps and running tools. It is important that steps
just connect and just do the most natural thing - and this is what Galaxy does.
This document just provides a mathematical formalism to that "what should just
intuitively work" that can be used to document test cases and help with implementation.
This is reference documentation not user documentation, Galaxy should just work.
:::

## Mapping

If a tool consumes a simple dataset parameter and produces a simple dataset parameter,
then any collection type may be "mapped over" the data input to that tool. The result of
that is the tool being applied to each element of the collection and "implicit collections"
being created from the outputs that are produced from those operations. Those implicit
collections have the same element identifiers in the same order as the input collection that is
mapped over. Each element of the implicit collections correspond to their own job and
Galaxy very naturally and intuitively parallelizes jobs without extra work from the user
and without any knowledge of the tool.


(BASIC_MAPPING_PAIRED)=
(BASIC_MAPPING_PAIRED_OR_UNPAIRED_PAIRED)=
(BASIC_MAPPING_PAIRED_OR_UNPAIRED_UNPAIRED)=
(BASIC_MAPPING_LIST)=
<details><summary>Examples</summary>

:::{admonition} Example: `BASIC_MAPPING_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{paired},\left\{\text{forward}=tool(i=d_f)[o], \text{reverse}=tool(i=d_r)[o]\right\}>\right\}$$

:::



:::{admonition} Example: `BASIC_MAPPING_PAIRED_OR_UNPAIRED_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired\_or\_unpaired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{paired\_or\_unpaired},\left\{\text{forward}=tool(i=d_f)[o], \text{reverse}=tool(i=d_r)[o]\right\}>\right\}$$

:::



:::{admonition} Example: `BASIC_MAPPING_PAIRED_OR_UNPAIRED_UNPAIRED` 
:class: note

Assuming,

* $ d_u $ is a dataset
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired\_or\_unpaired},\left\{ \text{ unpaired }=d_u \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{paired\_or\_unpaired},\left\{\text{unpaired}=tool(i=d_u)[o]\right\}>\right\}$$

:::



:::{admonition} Example: `BASIC_MAPPING_LIST` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{i1}=tool(i=d_1)[o],...,\text{in}=tool(i=d_n)[o]\right\}>\right\}$$

:::



</details><br>



The above description of mapping over inputs works naturally and as expected for
nested collections.


(NESTED_LIST_MAPPING)=
(BASIC_MAPPING_LIST_PAIRED_OR_UNPAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `NESTED_LIST_MAPPING` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{list},\left\{ \text{ o1 }=\left\{ \text{ inner }=d_1 \right\}, ..., \text{ on }=\left\{ \text{ inner }=d_n \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{list}:\text{list},\left\{\text{o1}=\left\{\text{inner}=tool(i=d_1)[o]\right\},...,\text{on}=\left\{\text{inner}=tool(i=d_n)[o]\right\}\right\}>\right\}$$

:::



:::{admonition} Example: `BASIC_MAPPING_LIST_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{list}:\text{paired\_or\_unpaired},\left\{\text{el1}=\left\{\text{forward}=tool(i=d_f)[o], \text{reverse}=tool(i=d_r)[o]\right\}\right\}>\right\}$$

:::



</details><br>




For tools with multiple data inputs, the tool can be executed with individual
datasets for the non-mapped over input and each tool execution will just be executed
with that dataset. The dataset not mapped over serves as the input for each execution.


(BASIC_MAPPING_INCLUDING_SINGLE_DATASET)=
<details><summary>Examples</summary>

:::{admonition} Example: `BASIC_MAPPING_INCLUDING_SINGLE_DATASET` 
:class: note

Assuming,

* $ d_1,...,d_n $, $ d_o $ are datasets
* $ tool \text{ is } (i: \text{ dataset }, i2: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C), i2=d_o) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{i1}=tool(i=d_1, i2=d_o)[o],...,\text{in}=tool(i=d_n, i2=d_o)[o]\right\}>\right\}$$

:::



</details><br>



If a tool consumes two input datasets and produces one output dataset, you can map two
collections with identical structure (same element identifiers in the same order) over
the respective inputs and the result is an implicit collection with the same structure
as the inputs and where each output in the implicit collection corresponds to the tool
being executed with the two inputs corresponding to that position in the input
collections.

The default behavior here is the collections are linked and the act of mapping over
inputs to the tool are sort of a flat map or a dot product. No extra dimensionality
in the resulting collections.

From a user perspective this means if you start with a collection and apply a bunch
of map over operations on tools - the results will all continue to match and work together
very naturally - again without extra work by the user and without extra knowledge
by the tool author.


(BASIC_MAPPING_TWO_INPUTS_WITH_IDENTICAL_STRUCTURE)=
<details><summary>Examples</summary>

:::{admonition} Example: `BASIC_MAPPING_TWO_INPUTS_WITH_IDENTICAL_STRUCTURE` 
:class: note

Assuming,

* $ d1_1,...,d1_n $, $ d2_1,...,d2_n $ are datasets
* $ tool \text{ is } (i: \text{ dataset }, i2: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C1 $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d1_1, ..., \text{ in }=d1_n \right\}\text{>} $
* $ C2 $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d2_1, ..., \text{ in }=d2_n \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C1), i2=\text{mapOver}(C2)) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{i1}=tool(i=d1_1, i2=d2_1)[o],...,\text{in}=tool(i=d1_n, i2=d2_n)[o]\right\}>\right\}$$

:::



</details><br>



## Reduction

Not all tool executions result in implicit collections and mapping
over inputs. Tool inputs of ``type`` ``data_collection`` can consume
collections directly and do not necessarily result in mapping over.

Tools that consume collections and output datasets effectively
reduce the dimension of the Galaxy data structure. When used at runtime
this is often referred to as a "reduction" in the code.


(COLLECTION_INPUT_PAIRED)=
(COLLECTION_INPUT_LIST)=
(COLLECTION_INPUT_PAIRED_OR_UNPAIRED)=
(COLLECTION_INPUT_LIST_PAIRED_OR_UNPAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `COLLECTION_INPUT_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



:::{admonition} Example: `COLLECTION_INPUT_LIST` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<list> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ el1 }=d_1, ..., \text{ eln }=d_n \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



:::{admonition} Example: `COLLECTION_INPUT_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired\_or\_unpaired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



:::{admonition} Example: `COLLECTION_INPUT_LIST_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list:paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



</details><br>



For nested collections where each rank is a ``list`` or a ``paired`` collection,
then collection inputs must match every part of the collection type input definition.


(COLLECTION_INPUT_LIST_NOT_CONSUMES_PAIRS)=
(COLLECTION_INPUT_PAIRED_NOT_CONSUMES_LIST)=
(COLLECTION_INPUT_LIST_PAIRED_NOT_CONSUMES_PAIRED_PAIRED)=
(COLLECTION_INPUT_LIST_PAIRED_OR_NOT_PAIRED_NOT_CONSUMES_PAIRED_PAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `COLLECTION_INPUT_LIST_NOT_CONSUMES_PAIRS` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



:::{admonition} Example: `COLLECTION_INPUT_PAIRED_NOT_CONSUMES_LIST` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



:::{admonition} Example: `COLLECTION_INPUT_LIST_PAIRED_NOT_CONSUMES_PAIRED_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list:paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired}:\text{paired},\left\{ \text{ forward }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}, \text{ reverse }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



:::{admonition} Example: `COLLECTION_INPUT_LIST_PAIRED_OR_NOT_PAIRED_NOT_CONSUMES_PAIRED_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list:paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired}:\text{paired},\left\{ \text{ forward }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}, \text{ reverse }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



</details><br>



In addition to explicit collection inputs, tool inputs of ``type`` ``data``
where ``multiple="true"`` can consume lists directly. This is likewise a
"reduction" and does not result in implicit collection creation.


(LIST_REDUCTION)=
<details><summary>Examples</summary>

:::{admonition} Example: `LIST_REDUCTION` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ dataset<multiple=true> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=C) == tool(i=[d_1,...,d_n])$$

:::



</details><br>



Paired collections cannot be reduced this way. ``paired`` is not meant
to represent a list/array/vector data structure - it is more like a tuple.


(PAIRED_REDUCTION_INVALID)=
(PAIRED_OR_UNPAIRED_REDUCTION_INVALID)=
<details><summary>Examples</summary>

:::{admonition} Example: `PAIRED_REDUCTION_INVALID` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset<multiple=true> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



:::{admonition} Example: `PAIRED_OR_UNPAIRED_REDUCTION_INVALID` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset<multiple=true> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired\_or\_unpaired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



</details><br>



## Sub-collection Mapping

![](https://planemo.readthedocs.io/en/master/_images/subcollection_mapping_identifiers.svg)


(MAPPING_LIST_PAIRED_OVER_PAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `MAPPING_LIST_PAIRED_OVER_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $
* $ C\_PAIRED $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C, '\text{paired}')) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{el1}=tool(i=C\_PAIRED)[o]\right\}>\right\}$$

:::



</details><br>



The natural extension of multiple data input parameters consuming list collections as described
above when discussing reductions is that nested lists of lists (``list:list``) can be mapped
over a multiple data input parameter. Each nested list will be reduced by this operation but the
results will be mapped over. The result will be a list with the same structure as the outer list
of the input collection.


(NESTED_LIST_REDUCTION)=
<details><summary>Examples</summary>

:::{admonition} Example: `NESTED_LIST_REDUCTION` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ dataset<multiple=true> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{list},\left\{ \text{ o1 }=\left\{ \text{ inner }=d_1 \right\}, ..., \text{ on }=\left\{ \text{ inner }=d_n \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C, '\text{list}')) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{o1}=tool(i=[d_1])[o],...,\text{on}=tool(i=[d_n])[o]\right\}>\right\}$$

:::



</details><br>



Just as a paired collection won't be reduced by a multiple data input, any sort of nested
collection ending in a paired collection cannot be mapped over such an input. So a multiple
data input parameter cannot be mapped over by a list of pairs (``list:paired``) for instance.


(LIST_PAIRED_REDUCTION_INVALID)=
(LIST_PAIRED_OR_UNPAIRED_REDUCTION_INVALID)=
<details><summary>Examples</summary>

:::{admonition} Example: `LIST_PAIRED_REDUCTION_INVALID` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset<multiple=true> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C, '\text{paired}'))\text{ is invalid}$$

:::



:::{admonition} Example: `LIST_PAIRED_OR_UNPAIRED_REDUCTION_INVALID` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ dataset<multiple=true> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C, '\text{paired\_or\_unpaired}'))\text{ is invalid}$$

:::



</details><br>



## paired_or_unpaired Collections

The collection type ``paired_or_unpaired`` is meant to serve as a stand-in for
an entity that can be either a single dataset or what is effectively a ``paired``
dataset collection. These collections either have one element with identifier
``unpaired`` or two elements with identifiers ``forward`` and ``reverse``.

Tools can declare a data_collection input with collection type ``paired_or_unpaired``
and that input will consume either an explicit ``paired_or_unpaired`` collection
normally or can consume a ``paired`` input.


(PAIRED_OR_UNPAIRED_CONSUMES_PAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `PAIRED_OR_UNPAIRED_CONSUMES_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $
* $ C_AS_MIXED = CollectionInstance<\text{paired\_or\_unpaired}, \left\{\text{forward}: d_f, \text{reverse}: d_r\right\}> $


then

$$tool(i=C) == tool(i=C_AS_MIXED)$$

:::



</details><br>




The inverse of this doesn't work intentionally. In some ways a ``paired`` collection
acts as a ``paired_or_unpaired`` collection but a ``paired_or_unpaired`` is not a paired
collection. This makes a lot of sense in terms of tools - a tool consuming a ``paired``
dataset expects to find both a ``forward`` and ``reverse`` element but these may not exist
in ``paired_or_unpaired`` collection.


(PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{paired\_or\_unpaired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



</details><br>




The same logic holds for mapping, lists of paired datasets (``list:paired``) can be mapped over these
``paired_or_unpaired`` inputs and mixed lists of pairs (``list:paired_or_unpaired``) cannot
be mapped over a ``paired`` input. Following the same logic, ``list:paired_or_unpaired`` cannot
be mapped over a ``list`` input or multiple data input.


(MAPPING_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED)=
(PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED_WHEN_MAPPING)=
(PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_LIST_WHEN_MAPPING)=
<details><summary>Examples</summary>

:::{admonition} Example: `MAPPING_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired},\left\{ \text{ el }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $
* $ C_AS_MIXED $ is $ \text{CollectionInstance<}\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ el }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) == tool(i=\text{mapOver}(C_AS_MIXED))$$

:::



:::{admonition} Example: `PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_PAIRED_WHEN_MAPPING` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ el }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C))\text{ is invalid}$$

:::



:::{admonition} Example: `PAIRED_OR_UNPAIRED_NOT_CONSUMED_BY_LIST_WHEN_MAPPING` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ el }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C))\text{ is invalid}$$

:::



</details><br>



This logic extends naturally into higher dimensional collections. A ``list:list:paired``
can be mapped over either a ``paired_or_unpaired`` input to produce a nested list (``list:list``)
or a ``list:paired_or_unpaired`` input to produce a flat list (``list``).


(MAPPING_LIST_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `MAPPING_LIST_LIST_PAIRED_OVER_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{list}:\text{paired},\left\{ \text{ o1 }=\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\} \right\}\text{>} $
* $ C_AS_MIXED $ is $ \text{CollectionInstance<}\text{list}:\text{list}:\text{paired\_or\_unpaired},\left\{ \text{ o1 }=\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) == tool(i=\text{mapOver}(C_AS_MIXED))$$

:::



</details><br>




In order for ``paired_or_unpaired`` collections to also act as a single dataset,
a flat list can be mapped over a such an input with a special sub collection mapping
type of 'single_datasets'.


(MAPPING_LIST_OVER_PAIRED_OR_UNPAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `MAPPING_LIST_OVER_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $
* $ C_AS_UNPAIRED_i = CollectionInstance<\text{paired\_or\_unpaired},\left\{\text{unpaired}=di\right\}> for i from 1...n $


then

$$tool(i=\text{mapOver}(C, '\text{single\_datasets}')) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{i1}=tool(i=C_AS_UNPAIRED_1)[o],...,\text{in}=tool(i=C_AS_UNPAIRED_n)[o]\right\}>\right\}$$

:::



</details><br>



This treatment of lists without pairing extends to nested structures naturally.
For instance, a list of list of datasets (``list:list``) can be mapped over a
``paired_or_unpaired`` input to produce a nested list of lists (``list:list``)
with a structure matching the input. Likewise, the nested list can be mapped over
a ``list:paired_or_unpaired`` input to produce a flat list with the same structure
as the outer list of the input.


(MAPPING_LIST_LIST_OVER_PAIRED_OR_UNPAIRED)=
(MAPPING_LIST_LIST_OVER_LIST_PAIRED_OR_UNPAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `MAPPING_LIST_LIST_OVER_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{list},\left\{ \text{ o1 }=\left\{ \text{ inner }=d_1 \right\}, ..., \text{ on }=\left\{ \text{ inner }=d_n \right\} \right\}\text{>} $
* $ C_AS_UNPAIRED_j = CollectionInstance<\text{paired\_or\_unpaired},\left\{\text{unpaired}=dj\right\}> for each \text{dataset} dj in C $


then

$$tool(i=\text{mapOver}(C, '\text{single\_datasets}')) \mapsto \left\{o: \text{collection}<\text{list}:\text{list},\left\{\text{o1}=\left\{\text{inner}=tool(i=C_AS_UNPAIRED_1)[o]\right\},...,\text{on}=\left\{\text{inner}=tool(i=C_AS_UNPAIRED_n)[o]\right\}\right\}>\right\}$$

:::



:::{admonition} Example: `MAPPING_LIST_LIST_OVER_LIST_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<list:paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{list},\left\{ \text{ o1 }=\left\{ \text{ inner }=d_1 \right\}, ..., \text{ on }=\left\{ \text{ inner }=d_n \right\} \right\}\text{>} $
* $ C_AS_LPU_i = \text{inner} \text{list} of C at position i, treated as \text{list}:\text{paired\_or\_unpaired} via \text{single\_datasets} $


then

$$tool(i=\text{mapOver}(C, '\text{list}:\text{paired\_or\_unpaired}')) \mapsto \left\{o: \text{collection}<\text{list},\left\{\text{o1}=tool(i=C_AS_LPU_1)[o],...,\text{on}=tool(i=C_AS_LPU_n)[o]\right\}>\right\}$$

:::



</details><br>



Due only to implementation time, the special casing of allowing paired_or_unpaired
act as both datasets and paired collections only works when it is the deepest
collection type. So while list:paired can be consumed by a list:paired_or_unpaired
input, a paired:list cannot be consumed by a paired_or_unpaired:list input though
it should be able to for consistency. We have focused our time on data structures
more likely to be used in actual Galaxy analyses given current and guessed future
usage.


## sample_sheet Collections

The collection type ``sample_sheet`` attaches typed, columnar metadata to each
element of a dataset collection. For mapping and type matching purposes,
``sample_sheet`` behaves identically to ``list`` - it can be mapped over tool
inputs, matched against ``list`` collection inputs, and composed with inner types
(``sample_sheet:paired``, ``sample_sheet:paired_or_unpaired``). The key asymmetry
is that while a ``sample_sheet`` output can satisfy a ``list`` input, a ``list``
output cannot satisfy a ``sample_sheet`` input - sample sheets carry metadata
that plain lists do not.


(SAMPLE_SHEET_MAPPING)=
(SAMPLE_SHEET_MATCHES_LIST)=
<details><summary>Examples</summary>

:::{admonition} Example: `SAMPLE_SHEET_MAPPING` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ dataset }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) \mapsto \left\{o: \text{collection}<\text{sample\_sheet},\left\{\text{i1}=tool(i=d_1)[o],...,\text{in}=tool(i=d_n)[o]\right\}>\right\}$$

:::



:::{admonition} Example: `SAMPLE_SHEET_MATCHES_LIST` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<list> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



</details><br>



Sub-collection mapping works the same as for ``list`` composites. A
``sample_sheet:paired`` can be mapped over a ``paired`` collection input,
extracting each inner pair and producing a ``sample_sheet`` implicit output.


(SAMPLE_SHEET_PAIRED_MAPPING_OVER_PAIRED)=
(SAMPLE_SHEET_PAIRED_MATCHES_LIST_PAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `SAMPLE_SHEET_PAIRED_MAPPING_OVER_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet}:\text{paired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $
* $ C\_PAIRED $ is $ \text{CollectionInstance<}\text{paired},\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C, '\text{paired}')) \mapsto \left\{o: \text{collection}<\text{sample\_sheet},\left\{\text{el1}=tool(i=C\_PAIRED)[o]\right\}>\right\}$$

:::



:::{admonition} Example: `SAMPLE_SHEET_PAIRED_MATCHES_LIST_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list:paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet}:\text{paired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



</details><br>



The ``paired_or_unpaired`` integration rules carry over from ``list`` to
``sample_sheet``. A flat ``sample_sheet`` can be mapped over a
``paired_or_unpaired`` input via ``single_datasets`` sub-collection mapping,
and ``sample_sheet:paired`` can be mapped over ``paired_or_unpaired`` just as
``list:paired`` can.


(SAMPLE_SHEET_MAPPING_OVER_PAIRED_OR_UNPAIRED)=
(SAMPLE_SHEET_PAIRED_MAPPING_OVER_PAIRED_OR_UNPAIRED)=
(SAMPLE_SHEET_PAIRED_OR_UNPAIRED_MATCHES_LIST_PAIRED_OR_UNPAIRED)=
<details><summary>Examples</summary>

:::{admonition} Example: `SAMPLE_SHEET_MAPPING_OVER_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $
* $ C_AS_UNPAIRED_i = CollectionInstance<\text{paired\_or\_unpaired},\left\{\text{unpaired}=di\right\}> for i from 1...n $


then

$$tool(i=\text{mapOver}(C, '\text{single\_datasets}')) \mapsto \left\{o: \text{collection}<\text{sample\_sheet},\left\{\text{i1}=tool(i=C_AS_UNPAIRED_1)[o],...,\text{in}=tool(i=C_AS_UNPAIRED_n)[o]\right\}>\right\}$$

:::



:::{admonition} Example: `SAMPLE_SHEET_PAIRED_MAPPING_OVER_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet}:\text{paired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $
* $ C_AS_MIXED $ is $ \text{CollectionInstance<}\text{sample\_sheet}:\text{paired\_or\_unpaired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=\text{mapOver}(C)) == tool(i=\text{mapOver}(C_AS_MIXED))$$

:::



:::{admonition} Example: `SAMPLE_SHEET_PAIRED_OR_UNPAIRED_MATCHES_LIST_PAIRED_OR_UNPAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<list:paired\_or\_unpaired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet}:\text{paired\_or\_unpaired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



</details><br>



The type matching is asymmetric: a ``sample_sheet`` output can satisfy a ``list``
input because sample sheets carry all the structural information lists have (plus
metadata). However, a ``list`` output cannot satisfy a ``sample_sheet`` input because
lists lack the ``column_definitions`` and per-element ``columns`` metadata that
sample sheet consumers expect.


(LIST_NOT_MATCHES_SAMPLE_SHEET)=
(LIST_PAIRED_NOT_MATCHES_SAMPLE_SHEET_PAIRED)=
(SAMPLE_SHEET_MATCHES_SAMPLE_SHEET)=
<details><summary>Examples</summary>

:::{admonition} Example: `LIST_NOT_MATCHES_SAMPLE_SHEET` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<sample\_sheet> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



:::{admonition} Example: `LIST_PAIRED_NOT_MATCHES_SAMPLE_SHEET_PAIRED` 
:class: note

Assuming,

* $ d_f $, $ d_r $ are datasets
* $ tool \text{ is } (i: \text{ collection<sample\_sheet:paired> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{list}:\text{paired},\left\{ \text{ el1 }=\left\{ \text{ forward }=d_f, \text{ reverse }=d_r \right\} \right\}\text{>} $


then

$$tool(i=C)\text{ is invalid}$$

:::



:::{admonition} Example: `SAMPLE_SHEET_MATCHES_SAMPLE_SHEET` 
:class: note

Assuming,

* $ d_1,...,d_n $ are datasets
* $ tool \text{ is } (i: \text{ collection<sample\_sheet> }) \Rightarrow \{ o: \text{ dataset } \} $
* $ C $ is $ \text{CollectionInstance<}\text{sample\_sheet},\left\{ \text{ i1 }=d_1, ..., \text{ in }=d_n \right\}\text{>} $


then

$$tool(i=C) \rightarrow \left\{o: \text{dataset}\right\}$$

:::



</details><br>



## Callable workflow boundaries

### Start with two samples and three references

A parent workflow passes two samples, `A = [X, Y]`, to a subworkflow input
that expects **one dataset**. Galaxy maps the subworkflow over the samples.
The parent also passes three references, `B = [P, Q, R]`, to a child input
that expects a **whole list**.

Inside the child, a tool processes each reference. Even if this tool never
reads the sample input, it belongs to the workflow being run for each sample.
It therefore runs **2 × 3 = 6 jobs**, with results grouped by sample:

```text
Before: 3 reference jobs          After: 6 reference jobs
list                             list:list
  P → result                       X
  Q → result                         P → result for X/P
  R → result                         Q → result for X/Q
                                     R → result for X/R
                                   Y
                                     P → result for Y/P
                                     Q → result for Y/Q
                                     R → result for Y/R
```

Previously, a branch disconnected from the sample input could run just
three jobs and omit the sample level from its output. Mapping now applies
to every executable step inside the child. A reference-only tool receives
the same reference contents for `X/P` and `Y/P`, but these are distinct jobs
and output datasets.

For the same child call, with no conditional skips:

| What a child tool consumes | Jobs | Output from a tool producing one dataset |
| --- | ---: | --- |
| One sample | 2 | `list`: one result under each of `X`, `Y` |
| One reference | 6 | `list:list`: `X`, `Y`, each containing `P`, `Q`, `R` |
| One sample and one reference | 6 | The same `list:list` structure |
| The complete reference list | 2 | `list`: one result under each of `X`, `Y` |

The reference input still expects a `list`; mapping the child adds an outer
level to its results without changing its declared input type. The
[example workflow](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/workflow/subworkflow_mapping_per_step.gxwf.yml)
and its [expected outputs](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/workflow/subworkflow_mapping_per_step.gxwf-tests.yml)
make this example executable.

### Combining independent and linked inputs

An **axis** records a collection choice used when scheduling a step. Here,
one axis chooses a sample; a second chooses a reference. A **coordinate**
is a particular choice, such as `(X, P)`. An axis can cover several nested
collection levels; it does not always correspond to one `list` in a type.

Every child step inherits the sample axis from the subworkflow call. A
reference axis introduced inside the child follows it. Independent axes
produce every combination, in sample-then-reference order. Downstream
steps recognize axes already carried by their inputs, so consuming these
six results produces six jobs without adding the sample axis again.

**Linked inputs advance together.** For example, two reference lists
`[P, Q, R]` and `[U, V, W]`, linked at the same child step, pair as
`(P, U)`, `(Q, V)`, `(R, W)` for each sample. This gives six jobs. Linking
still requires compatible collection structures; it does not create all
nine reference combinations.

Nested subworkflows inherit these choices in the same order, once per
boundary. The [nested example](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/workflow/subworkflow_mapping_nested_passthrough.gxwf-tests.yml)
checks that another child call does not duplicate the outer level.

### Returning an input unchanged

A **pass-through output** connects a child input directly to a child output.
It creates no producer jobs, but its collection shape still reflects the
mapped call:

| Child output | Returned value for samples `X`, `Y` |
| --- | --- |
| The mapped sample input | `X → X`, `Y → Y` |
| A separate, single dataset `D` | `X → D`, `Y → D` |
| The direct reference list | `X → [P, Q, R]`, `Y → [P, Q, R]` |

Galaxy reuses an existing collection when it already covers the complete
mapping. Otherwise it builds the required collection structure. Each new
inner collection has its own identity, while its dataset entries can refer
to the same original history datasets. No data files are copied merely to
repeat a pass-through value.

Identifiers, element order, collection types, and sample-sheet rows and
columns are preserved. Tags on newly created collection associations are
not copied by this mechanism; shared dataset entries retain their metadata
and tags.

### Empty inputs and skipped calls

An empty sample list schedules no child jobs. Outputs retain their declared
nesting: the reference branch returns an empty `list:list`, for example.

If a condition skips sample `Y`, a pass-through output must not expose `Y`'s
input as a successful result. For a known reference list, Galaxy preserves
its identifiers and inserts skipped `expression.json` datasets containing
null values at the leaves. The result retains the `Y` position and its
`P`, `Q`, `R` positions.

A tool that discovers collection elements only while running presents a
different case: a skipped tool has not discovered its inner shape. Existing
behavior can leave that branch empty. This chapter does not equate that
empty branch with a null collection. The API tests named below cover both
known-shape pass-through and dynamically discovered outputs.

### Compatibility and implementation

Existing workflows with independent child branches can schedule more jobs
and return an extra outer collection level. Review downstream consumers
that previously received a flat reference list. If reference processing
should happen only once, place it outside the mapped subworkflow and pass
its results into the child.

Galaxy records one child **invocation** for this call. That record groups
the child steps; each tool step records its own jobs at the relevant
coordinates. Thus one child invocation and six reference jobs describe
different parts of the same execution.

The scheduler persists each output's mapping axes and their association
with collection levels. It restores them before scheduling dependent
steps on a later pass. This prevents a resumed step from forgetting or
counting an inherited mapping twice. The scheduling integration test runs
with a one-job-per-iteration limit to exercise this recovery. A nested
pass-through must retain its sample and reference choices even when its
consumer is scheduled later. Likewise, approving a review pause for two
samples must resume two consumer jobs with the original sample grouping.

A child resumes through its parent so it retains that mapping context.
The parent's subworkflow step stays pending until all child work has been
scheduled, including tools whose outputs are not exported, even when
pass-through outputs are already available. Those jobs may still be running
when the step finishes scheduling.
Cancelling a paused child also cancels its parent; consumers waiting for
review remain unscheduled.

### Limits and separate questions

Mapped dataset and collection pass-throughs are supported. Mapped raw
parameter/`output_value` pass-throughs, such as returning an input number
directly, are rejected: persisting a collection of those values requires a
separate representation.

Some deeper linked structures cannot currently be reconciled. In
particular, a linked input may need more collection levels than the
corresponding part of an already refined inherited axis can select.
Galaxy rejects this case rather than silently pairing the wrong elements;
`test_direct_linked_peer_deeper_than_embedded_component_is_rejected`
records a concrete example.

These mapping rules determine which execution positions and collection
levels exist. They do not settle when a tool's filtered output should
become null, when an optional input should use its default, or whether an
ordinary multiple-data input should remove absent entries. Those policies
need their own examples and tests. Known-shape conditional pass-throughs
above specify one absence case, not a general absence policy.

### Where to verify each rule

These references describe test coverage, not the outcome of a particular
test run:

| Rule | Tests |
| --- | --- |
| Job counts, output shape, shared dataset identities | [API tests](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/api/test_workflows.py): `test_subworkflow_mapping_callable_boundary_job_cardinality` |
| Independent products, linked pairing, empty axes | [Collection matcher tests](https://github.com/galaxyproject/galaxy/blob/dev/test/unit/data/dataset_collections/test_matching.py): `test_independent_mapping_axes_cross_product_in_stable_order`, `test_linked_inputs_slice_in_zip_order` |
| Known-shape conditional pass-throughs and dynamic skipped branches | API tests: `test_run_workflow_conditional_subworkflow_step_map_over_expression_tool` and its `with_extra_nesting` variants |
| Partial pass-through structure and rejected cases | [Workflow module tests](https://github.com/galaxyproject/galaxy/blob/dev/test/unit/workflows/test_modules.py): `test_partial_refined_axis_passthrough_is_broadcast_over_missing_suffix`, `test_mapped_parameter_passthrough_is_explicitly_unsupported`, and the deeper linked-input test above |
| Recovery across scheduling rounds; no repeated pass-through collections | [Scheduling integration tests](https://github.com/galaxyproject/galaxy/blob/dev/test/integration/test_workflow_scheduling_options.py): `test_subworkflow_mapping_axes_survive_scheduling_rounds`, `test_conditional_subworkflow_passthrough_is_materialized_once` |
| Nested pass-through consumed after a scheduling delay, including unexported child work | Scheduling integration tests: `test_nested_passthrough_consumer_keeps_mapping_after_scheduling_delay` |
| Review approval preserves mapping; child cancellation cancels the parent | [Pause integration test](https://github.com/galaxyproject/galaxy/blob/dev/test/integration/test_subworkflow_pause_mapping.py): `test_child_pause_preserves_mapping_and_cancellation` |
| Editor input/output types and connection order | [Workflow-editor terminal tests](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Workflow/Editor/modules/terminals.test.ts) |


## Type Compatibility Algebra

This section is for implementers. It describes the three operations that
answer "do these collection types fit together?" — used at workflow
editor connection time and at runtime when sibling inputs are matched
under a common map-over.

### The lattice

The base types form a small subtype lattice:

```
list                paired_or_unpaired
 |                    |
sample_sheet         paired
```

Edges are subtype relations. A `sample_sheet` value carries column
metadata that a `list` does not, so it can be substituted where a
`list` is required (information is preserved); the reverse is not safe.
A `paired` value always has two elements; `paired_or_unpaired` admits
1 or 2, so a `paired` can be substituted where `paired_or_unpaired` is
required, but not the reverse.

Nesting composes. `list:paired_or_unpaired` is a supertype of both
`list:paired` and `list` (the latter via the "single-dataset wrapped
as unpaired" interpretation), so it has two incomparable subtypes.

### Three operations

| Operation | Symmetry | Question | Used at |
|---|---|---|---|
| `accepts(other)` | Asymmetric | Does an input slot of type `self` accept an output of type `other`? | Workflow-editor edge validation |
| `compatible(other)` | Symmetric | Do `self` and `other` match such that they could drive a common map-over over sibling inputs of one tool? | Sibling-matching: matching sibling HDCAs / sibling map-over states under a common mapping |
| `can_map_over(other)` | Asymmetric | Does `self` have proper subcollections of type `other` — i.e. can `self` be mapped over to feed an `other` slot? | Connection-time map-over decisions; runtime `effective_collection_type` arithmetic |

Conventions: `input_type.accepts(output_type)` for direct edges;
`output_type.can_map_over(input_type)` for map-over. `accepts` and
`can_map_over` differ in that `accepts` is the direct-edge case
where ranks already align, while `can_map_over` is the strict nesting
case where the output has *more* rank than the input. `compatible`
is symmetric and either side may go first.

`compatible(a, b)` is implemented as `a.accepts(b) or b.accepts(a)`.

### Where each is used

- `accepts` is called at single-edge validation: connecting one output
  to one input. The asymmetry between input and output sides matters
  here. Examples: `connection_types.can_match`,
  `query.HistoryQuery.direct_match`, and the workflow-editor input
  attachment paths in `terminals.ts`.

- `compatible` is called when two collections must drive a common
  map-over as siblings. Neither side is the input slot; both are
  concrete shapes (observed HDCA shapes at runtime, sibling map-over
  states at connection time). Order of arrival must not change the
  answer. Examples: Python `Tree.compatible_shape` (matching.py,
  execute.py) and the `mappingConstraints` checks in `terminals.ts`.

- `can_map_over` is called when deciding whether an output of higher
  rank can drive a map-over into a lower-rank input — for instance, a
  `list:paired` output feeding a `paired` input by iterating the outer
  list. The Python and TypeScript names match
  (`can_map_over` / `canMapOver`) because it is the same operational
  question in both layers.

Routing a sibling-matching question through `accepts` instead of
`compatible` produces order-dependent behavior — which sibling input
arrived first changes whether the workflow validates. This was a real
bug in earlier revisions of both the Python and TypeScript code.

### Worked examples

- `paired.accepts(paired_or_unpaired)` is `False`. A 1-element
  paired_or_unpaired output cannot be connected to an input slot
  that strictly requires a pair. Test: `test_paired_accepts_relation`.

- `paired.compatible(paired_or_unpaired)` is `True`. If both observed
  sibling collections happen to align in cardinality, they match for
  sibling iteration; cardinality checking happens later at the
  children level. Test:
  `test_paired_and_paired_or_unpaired_match_symmetric`.

- `sample_sheet.accepts(list)` is `False`; `list.accepts(sample_sheet)`
  is `True`. Tests:
  `test_sample_sheet_accepts_relation`, workflow editor
  `"rejects list -> sample_sheet connection (asymmetry)"`.

- `sample_sheet.compatible(list)` and `list.compatible(sample_sheet)`
  are both `True`. Tests: `test_compatible`,
  `test_tree_compatible_shape_sample_sheet_list_symmetric`.

### Cross-language synchronization

The Python implementation lives in
`lib/galaxy/model/dataset_collections/type_description.py`. The
TypeScript implementation lives in
`client/src/components/Workflow/Editor/modules/collectionTypeDescription.ts`.
Both must stay in sync; method names and conventions are identical.


