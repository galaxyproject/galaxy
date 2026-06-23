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



