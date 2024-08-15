import copy
import os
from collections import namedtuple

import dictobj

Path = namedtuple("Path", ("path", "id", "options"))


class Node(dictobj.DictionaryObject):
    """
    Copyright 2012 "Grim Apps"

     Licensed under the Apache License, Version 2.0 (the "License");
     you may not use this file except in compliance with the License.
     You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

     Unless required by applicable law or agreed to in writing, software
     distributed under the License is distributed on an "AS IS" BASIS,
     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
     See the License for the specific language governing permissions and
     limitations under the License.

    Helper class written by William Grim - grimwm
    Original repo: https://github.com/grimwm/py-jstree
    Code adjusted according to the idea of Frank Blechschmidt - FraBle
    Thank you!
    ************************
    This class exists as a helper to the JSTree.  Its "jsonData" method can
    generate sub-tree JSON without putting the logic directly into the JSTree.

    This data structure is only semi-immutable.  The JSTree uses a directly
    iterative (i.e. no stack is managed) builder pattern to construct a
    tree out of paths.  Therefore, the children are not known in advance, and
    we have to keep the children attribute mutable.
    """

    def __init__(self, path, oid, **kwargs):
        """
        kwargs allows users to pass arbitrary information into a Node that
        will later be output in jsonData().  It allows for more advanced
        configuration than the default path handling that JSTree currently allows.
        For example, users may want to pass "attr" or some other valid jsTree options.

        Example:
          >>> node = Node('a', None)
          >>> assert node._items == {'text': 'a', 'children': dictobj.MutableDictionaryObject({})}
          >>> assert node.jsonData() == {'text': 'a'}

          >>> node = Node('a', 1)
          >>> assert node._items == {'text': 'a', 'children': dictobj.MutableDictionaryObject({}), 'li_attr': dictobj.DictionaryObject({'id': 1}), 'id': 1}
          >>> assert node.jsonData() == {'text': 'a', 'id': 1, 'li_attr': {'id': 1}}

          >>> node = Node('a', 5, icon="folder", state = {'opened': True})
          >>> assert node._items == {'text': 'a', 'id': 5, 'state': dictobj.DictionaryObject({'opened': True}), 'children': dictobj.MutableDictionaryObject({}), 'li_attr': dictobj.DictionaryObject({'id': 5}), 'icon': 'folder'}
          >>> assert node.jsonData() == {'text': 'a', 'state': {'opened': True}, 'id': 5, 'li_attr': {'id': 5}, 'icon': 'folder'}
        """
        super().__init__()

        children = kwargs.get("children", {})
        if len([key for key in children if not isinstance(children[key], Node)]):
            raise TypeError(f"One or more children were not instances of '{Node.__name__}'")
        if "children" in kwargs:
            del kwargs["children"]
        self._items["children"] = dictobj.MutableDictionaryObject(children)

        if oid is not None:
            li_attr = kwargs.get("li_attr", {})
            li_attr["id"] = oid
            kwargs["li_attr"] = li_attr
            self._items["id"] = oid

        self._items.update(dictobj.DictionaryObject(**kwargs))
        self._items["text"] = path

    def jsonData(self):
        children = [self.children[k].jsonData() for k in sorted(self.children)]
        output = {}
        for k in self._items:
            if "children" == k:
                continue
            if isinstance(self._items[k], dictobj.DictionaryObject):
                output[k] = self._items[k].asdict()
            else:
                output[k] = self._items[k]
        if len(children):
            output["children"] = children
        return output


class JSTree(dictobj.DictionaryObject):
    """
    An immutable dictionary-like object that converts a list of "paths"
    into a tree structure suitable for jQuery's jsTree.
    """

    def __init__(self, paths, **kwargs):
        """
        Take a list of paths and put them into a tree.  Paths with the same prefix should
        be at the same level in the tree.

        kwargs may be standard jsTree options used at all levels in the tree.  These will be outputted
        in the JSON.

        """
        if len([p for p in paths if not isinstance(p, Path)]):
            raise TypeError(f"All paths must be instances of '{Path.__name__}'")

        super().__init__()

        root = Node("", None, **kwargs)
        for path in sorted(paths):
            curr = root
            subpaths = path.path.split(os.path.sep)
            for i, subpath in enumerate(subpaths):
                if subpath not in curr.children:
                    opt = copy.deepcopy(kwargs)
                    if len(subpaths) - 1 == i:
                        oid = path.id
                        opt.update(path.options) if path.options is not None else None
                    else:
                        oid = None
                    curr.children[subpath] = Node(subpath, oid, **opt)
                    # oid = path.id if len(subpaths) - 1 == i else None
                    # curr.children[subpath] = Node(subpath, oid, **kwargs)
                curr = curr.children[subpath]
        self._items["_root"] = root

    def pretty(self, root=None, depth=0, spacing=2):
        """
        Create a "pretty print" represenation of the tree with customized indentation at each
        level of the tree.
        """
        if root is None:
            root = self._root
        fmt = "%s%s/" if root.children else "%s%s"
        s = fmt % (" " * depth * spacing, root.text)
        for child in root.children:
            child = root.children[child]
            s += f"\n{self.pretty(child, depth + 1, spacing)}"
        return s

    def jsonData(self):
        """
        Returns a copy of the internal tree in a JSON-friendly format,
        ready for consumption by jsTree.  The data is represented as a
        list of dictionaries, each of which are our internal nodes.

        """
        return [self._root.children[k].jsonData() for k in sorted(self._root.children)]
