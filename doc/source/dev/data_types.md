# Data Types

## Contributing

If you're writing data types for local tools all data types
can be added directly to your Galaxy instance, but if you're
publishing tools to the Galaxy Toolshed we strongly recommend
adding all referenced data types upstream to Galaxy itself.
Basic information on contributing to Galaxy can be found in
the
[CONTRIBUTING documentation](https://github.com/galaxyproject/galaxy/blob/dev/CONTRIBUTING.md).

The rest of this document contains the basics of how to create and register
data types in Galaxy but we've noticed some common problems with simple
implementations that can cause serious problems on production servers.
When adding new data types to Galaxy please copy this production checklist
into your PR and update it with your answers to help use avoid these problems
in the future.

```
## Production Data Types Checklist

- Do any of your ``sniff``, ``set_meta``, ``set_peek`` implementations for data types 
  potentially use an  unbounded amount of memory. This will happen most often
  if they read an whole file into memory. This is not allowed even if you would
  expect these files to typically be small.
  - [ ] No.
- Does your ``sniff`` implementation read through the entirety of the file? This
  is never allowed for production data types.
  - [ ] No.
- Do either of your ``set_meta`` or ``set_peek`` implementations read through
  the entirety of the file? This is generally discouraged but if you feel
  it substantially improves the usability of the datatype please indicate why
  below.
  - [ ] No.
  - [ ] Yes. *Replace THIS sentence with the reason.*
- Does your datatype include metadata elements? In general metadata should not
  take the place of say a data type viewer or visualization, metadata should be
  used by the tools that consume this datatype.
  - [ ] No.
  - [ ] Yes. *Replace THIS sentence with how tools will consume this metadata.*
```

## Adding a New Data Type (Subclassed)

This specification describes the Galaxy source code
changes required to add support for a new data type.

Every Galaxy dataset is associated with a datatype
which can be determined by the file extension (or
format in the history item). Within Galaxy, supported
datatypes are contained in the
`galaxy.datatypes.registry:Registry` class, which has
the responsibility of mapping extensions to datatype
instances. At start up this registry is initialized
with data type values from the `datatypes_conf.xml`
file. All data type classes are a subclass of the
`galaxy.datatypes.data:Data` class.

We'll pretend to add a new datatype format named
`Foobar` whose associated file extension is `foo` to
our local Galaxy instance as a way to provide the
details for adding support for new data types. Our
example `Foobar` data type will be a subclass of
`galaxy.datatypes.tabular.Tabular`.

### Step 1: Register Data Type

We'll add the new data type to the `<registration>`
tag section of the `datatypes_conf.xml` file. Sample
`<datatype>` tag attributes in this section are:

```xml
<datatype extension="ab1" type="galaxy.datatypes.images:Ab1" mimetype="application/octet-stream" display_in_upload="true"/>
```

where

- `extension` - the data type's Dataset file extension (e.g., `ab1`, `bed`,
  `gff`, `qual`, etc.). The extension must consist only of lowercase letters,
  numbers, `_`, `-`, and `.`.
- `type` - the path to the class for that data type.
- `mimetype` - if present (it's optional), the data type's mime type
- `display_in_upload` - if present (it's optional and defaults to False), the
  associated file extension will be displayed in the "File Format" select list
  in the "Upload File from your computer" tool in the "Get Data" tool section of
  the tool panel.

**Note:** If you do not wish to add extended
functionality to a new datatype, but simply want
to restrict the output of a set of tools to be used
in another set of tools, you can add the flag
`subclass="True"` to the datatype definition line.

Example:

```xml
<datatype extension="my_tabular_subclass" type="galaxy.datatypes.tabular:Tabular" subclass="True"/>
```

### Step 2: Sniffer

Galaxy tools are configured to automatically set the
data type of an output dataset. However, in some
scenarios, Galaxy will attempt to determine the data
type of a file using a sniffer (e.g., uploading a
file from a local disk with 'Auto-detect' selected in
the File Format select list). The order in which
Galaxy attempts to determine data types is critical
because some formats are much more loosely defined
than others. The order in which the sniffer for each
data type is applied to the file should be most
rigidly defined formats first followed by less and
less rigidly defined formats, with the most loosely
defined format last, and then a default format
associated with the file if none of the data type
sniffers were successful. The order in which data
type sniffers are applied to files is implicit in the
`<sniffers>` tag set section of the
`datatypes_conf.xml` file. We'll assume that the
format of our Foobar data type is fairly rigidly
defined, so it can be placed closer to the start of
the sniff order.
```xml
<sniffers>
    <sniffer type="galaxy.datatypes.sequence:Maf"/>
    <sniffer type="galaxy.datatypes.sequence:Lav"/>
    <sniffer type="galaxy.datatypes.tabular:Foobar"/>
```


### Step 3: Data Type Class

We'll now add the `Foobar` class to
`lib/galaxy/datatypes/tabular.py`. Keep in mind that
your new data type class should be placed in a file
that is appropriate (based on its superclass), and
that the file will need to be imported by
`lib/galaxy/datatypes/registry.py`. You will need to
include a `file_ext` attribute to your class and
create any necessary functions to override the
functions in your new data type's superclass (in our
example, the `galaxy.datatypes.tabular.Tabular` class).
In our example below, we have set our class's
`file_ext` attribute to "foo" and we have overridden
the `__init__()`, `init_meta()` and `sniff()`
functions. It is important to override functions
(especially the meta data and sniff functions) if the
attributes of your new class differ from those of its
superclass. Note: sniff functions are not required to
be included in new data type classes, but if the sniff
function is missing, Galaxy will call the superclass
method.

```python
from galaxy.datatypes.sniff import get_headers
from galaxy.datatypes.tabular import Tabular


class Foobar(Tabular):
    """Tab delimited data in foo format"""
    file_ext = "foo"

    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True)


    def __init__(self, **kwd):
        """Initialize foobar datatype"""
        Tabular.__init__(self, **kwd)
        self.do_something_else()


    def init_meta(self, dataset, copy_from=None):
        Tabular.init_meta(self, dataset, copy_from=copy_from)
        if elems_len == 8:
            try:
                map(int, [hdr[6], hdr[7]])
                proceed = True
            except:
                pass


    def sniff(self, filename):
        headers = get_headers(filename, '\t')
        try:
            if len(headers) < 2:
                return False
            for hdr in headers:
                if len(hdr) > 1 and hdr[0] and not hdr[0].startswith('#'):
                    if len(hdr) != 8:
                        return False
                    try:
                        map(int, [hdr[6], hdr[7]])
                    except:
                        return False
                # Do other necessary checking here...
        except:
            return False
        # If we haven't yet returned False, then...
        return True

    ...
```

That should be it! If all of your code is
functionally correct you should now have support for
your new data type within your Galaxy instance.

## Adding a New Data Type (completely new)

### Basic Datatypes
In this [real life example](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/datatypes/sequence.py),
we'll add a datatype named `Genbank`, to support
GenBank files.

First, we'll set up a file named `sequence.py` in
`lib/galaxy/datatypes/sequence.py`. This file could
contain some of the standard sequence types, though
we'll only implement GenBank.

```python
"""
Classes for all common sequence formats
"""
import logging

from galaxy.datatypes import data

log = logging.getLogger(__name__)

class Genbank(data.Text):
    """Class representing a Genbank sequence"""
    file_ext = "genbank"
```

This is all you need to get started with a datatype.
Now, load it into your `datatypes_conf.xml` by adding
the following line:

```xml
<datatype extension="genbank" type="galaxy.datatypes.sequence:Genbank" display_in_upload="True" />
```

and start up your server, the datatype will be available.

### Adding a Sniffer

Datatypes can be "sniffed", their formats can be
automatically detected from their contents. For
GenBank files that's extremely easy to do, the first
5 characters will be `LOCUS`, according to section
3.4.4 of the [specification](ftp://ftp.ncbi.nih.gov/genbank/gbrel.txt).

To implement this in our tool we first have to add
the relevant sniffing code to our `Genbank` class in
`sequence.py`.

```python
    def sniff(self, filename):
        header = open(filename).read(5)
        return header == 'LOCUS'
```

and then we have to register the sniffer in
`datatypes_conf.xml`.

```xml
<sniffer type="galaxy.datatypes.sequence:Genbank"/>
```

Once that's done, restart your server and try
uploading a `genbank` file. You'll notice that the
filetype is automatically detected as `genbank` once
the upload is done.

### More Features

One of the useful things your datatype can do is
provide metadata. This is done by adding metadata
entries inside your class like this:

```python
class Genbank(data.Text):
    file_ext = "genbank"

    MetadataElement(name="number_of_sequences", default=0, desc="Number of sequences", readonly=True, visible=True, optional=True, no_value=0)
```

Here we have a `MetadataElement`, accessible in
methods with a dataset parameter from
`dataset.metadata.number_of_sequences`. There are a
couple relevant functions you'll want to override
here:

*  ```python
   set_peek(self, dataset, is_multi_byte=False)
   ```
*  ```python
   set_meta(self, dataset, **kwd)
   ```

The `set_peek` function is used to determine the blurb
of text that will appear to users above the preview
(first 5 lines of the file, the file peek), informing
them about metadata of a sequence. For `genbank` files,
we're probably interested in how many genome/records
are contained within a file. To do that, we need to
count the number of times the word LOCUS appears as
the first five characters of a line. We'll write a
function named `_count_genbank_sequences`.

```python
    def _count_genbank_sequences(self, filename):
        count = 0
        with open(filename) as gbk:
            for line in gbk:
                if line[0:5] == 'LOCUS':
                    count += 1
        return count
```

Which we'll call in our `set_meta` function, since
we're setting metadata about the file.

```python
    def set_meta(self, dataset, **kwd):
        dataset.metadata.number_of_sequences = self._count_genbank_sequences(dataset.get_file_name())
```

Now we'll need to make use of this in our `set_peek`
override:

```python
    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            # Add our blurb
            if (dataset.metadata.number_of_sequences == 1):
                dataset.blurb = "1 sequence"
            else:
                dataset.blurb = "%s sequences" % dataset.metadata.number_of_sequences
            # Get standard text peek from dataset
            dataset.peek = data.get_file_peek(dataset.get_file_name(), is_multi_byte=is_multi_byte)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
```

This function will be called during metadata setting.
Try uploading a multi record `genbank` file and testing
it out. If you don't have a multi-record `genbank` file,
simply concatenate a single file together a couple
times and upload that.

By now you should have a complete GenBank parser in
`sequence.py` that looks about like the following:

```python
from galaxy.datatypes import data
from galaxy.datatypes.metadata import MetadataElement
import logging
log = logging.getLogger(__name__)


class Genbank(data.Text):
    file_ext = "genbank"

    MetadataElement(name="number_of_sequences", default=0, desc="Number of sequences", readonly=True, visible=True, optional=True, no_value=0)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            # Add our blurb
            if (dataset.metadata.number_of_sequences == 1):
                dataset.blurb = "1 sequence"
            else:
                dataset.blurb = "%s sequences" % dataset.metadata.number_of_sequences
            # Get
            dataset.peek = data.get_file_peek(dataset.get_file_name(), is_multi_byte=is_multi_byte)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        return 'text/plain'

    def sniff(self, filename):
        header = open(filename).read(5)
        return header == 'LOCUS'

    def set_meta(self, dataset, **kwd):
        """
        Set the number of sequences in dataset.
        """
        dataset.metadata.number_of_sequences = self._count_genbank_sequences(dataset.get_file_name())

    def _count_genbank_sequences(self, filename):
        """
        This is not a perfect definition, but should suffice for general usage. It fails to detect any
        errors that would result in parsing errors like incomplete files.
        """
        # Specification for the genbank file format can be found in
        # ftp://ftp.ncbi.nih.gov/genbank/gbrel.txt
        # in section 3.4.4 LOCUS Format
        count = 0
        with open(filename) as gbk:
            for line in gbk:
                if line[0:5] == 'LOCUS':
                    count += 1
        return count
```

## Composite Datatypes

Composite datatypes can be used as a more structured way to contain individual history items which are composed of multiple files. The `Rgenetics` package for Galaxy has been implemented using Composite Datatypes; for real-life examples, examine the configuration files (particularly `lib/galaxy/datatypes/genetics.py`) included with the distribution.

In composite datatypes, there is one "primary" data file and any number of specified "component" files. The primary data file is a base dataset object and the component files are all located in a directory associated with that base dataset. There are two types of composite datatypes: basic and auto_primary_file. In **basic** composite datatypes, the primary data file must be written by tools or provided directly during upload. In **auto_primary_file** composite datatypes, the primary data file is generated automatically by the Framework; all tool-writable or uploadable files are stored in the directory associated with the primary file.

### Creating Composite Datatypes

A datatype can be set to composite by setting the `composite_type` flag. There are 3 valid options:

-  None (not a composite datatype)
-  `basic`
-  `auto_primary_file`


### Defining Basic Composite Datatypes

The example below defines a basic composite datatype which is composed of 2 component files along with a tool-written or user-uploaded primary file. In this example the primary file is a report summarizing the results. The two component files (`results.txt`, `results.dat`) contain the results; `results.txt` is a text file and is handled as such during upload whereas `results.dat` is flagged as binary, allowing a binary file to be uploaded for that component. During upload, 3 sets of file upload/paste interfaces are provided to the user. A file must be provided for the primary (index) file as well as `results.txt`; `results.dat` is flagged as optional so may be left blank.
```python
class BasicComposite(Text):

    composite_type = 'basic'


    def __init__ (self, **kwd):
        Text. __init__ (self, **kwd)
        self.add_composite_file('results.txt')
        self.add_composite_file('results.dat', is_binary = True, optional = True)
```

These files can be specified on the command line in the following fashion:

```xml
<command>someTool.sh '$input1' '${os.path.join($input1.extra_files_path, 'results.txt')}'
'${os.path.join($input1.extra_files_path, 'results.dat')}' '$output1'</command>
```

If a tool is aware of the file names for a datatype, then only `input1.extra_files_path` needs to be provided.

There are cases when it is desirable for the composite filenames to have varying names, but be of a similar form; for an example of this see `Rgenetics` below.


### Defining Auto Primary File Composite Datatypes

The example below defines an auto primary file composite datatype which is composed of 2 component files along with a framework generated file. In this example the primary file is an html page containing download links to the individual result files. The two component files (`results.txt`, `results.dat`) contain the results; `results.txt` is a text file and is handled as such during upload whereas `results.dat` is flagged as binary, allowing a binary file to be uploaded for that component. During upload, 2 sets of file upload/paste interfaces are provided to the user. A file must be provided for `results.txt` whereas `results.dat` is flagged as optional so may be left blank.

In this composite type, the primary file is generated using the `generate_primary_file` method specified in the datatype definition. The `generate_primary_file` method here loops through the defined components and creates a link to each.
```python
class AutoPrimaryComposite(Text):

    composite_type = 'auto_primary_file'


    def __init__ (self, **kwd):
        Text. __init__ (self, **kwd)
        self.add_composite_file('results.txt')
        self.add_composite_file('results.dat', is_binary=True, optional=True)


    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>Files for Composite Dataset (%s)</title></head><p/>This composite dataset is composed of the following files:<p/><ul>' % (self.file_ext)]
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).iteritems():
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            rval.append('<li><a href="%s">%s</a>%s' % (composite_name, composite_name, opt_text))
        rval.append('</ul></html>')
        return "\n".join(rval)
```

These files can be specified on the command line in the following fashion:
```xml
<command>someTool.sh ${os.path.join($input1.extra_files_path, 'results.txt')} ${os.path.join($input1.extra_files_path, 'results.dat')} $output1</command>
```


### Advanced Topics: `Rgenetics` Example

`Rgenetics` datatypes are defined as composite datatypes. The tools in this package rely heavily on the contents of a filename for analysis and reporting. In this case it is desirable for the filenames of the components to vary slightly, but maintain a common form. To do this, we use a special metadata parameter that can only be set at dataset creation (i.e. upload). This example uses the metadata parameter **base_name** to specify part of the components' filenames.
```python
class Lped(Text):
    MetadataElement(name="base_name", desc="base name for all transformed versions of this genetic dataset", default="galaxy", readonly=True, set_in_upload=True)


    composite_type = 'auto_primary_file'
    file_ext="lped"


    def __init__(self, **kwd):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file('%s.ped', description='Pedigree File', substitute_name_with_metadata='base_name', is_binary=True)
        self.add_composite_file('%s.map', description='Map File', substitute_name_with_metadata='base_name', is_binary=True)


    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>Files for Composite Dataset (%s)</title></head><p/>This composite dataset is composed of the following files:<p/><ul>' % (self.file_ext)]
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).iteritems():
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            rval.append('<li><a href="%s">%s</a>%s' % (composite_name, composite_name, opt_text))
        rval.append('</ul></html>')
        return "\n".join(rval)
```

The file specified as `%s.ped` is found at `${os.path.join($input1.extra_files_path, '%s.ped' % input1.metadata.base_name)}`.

It should be noted that changing the datatype of datasets which use this substitution method will cause an error if the metadata parameter 'base_name' does not exist in a datatype that the dataset is set to. This is because the value within 'base_name' will be lost -- if the datatype is set back to the original datatype, the default metadata value will be used and the filenames might not match the basename.

For this reason, users are not allowed to change the datatype of dataset between a composite datatype and any other datatype. This can be enforced by setting the `allow_datatype_change` attribute of a datatype class to `False`.

## Galaxy Tool Shed - Data Types

**Note:** These are deprecated and shouldn't be used. If you find old
documentation recommending these, please remove it.
