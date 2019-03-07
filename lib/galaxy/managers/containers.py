"""
Manager mixins to unify the interface into things that can contain: Datasets
and other (nested) containers.

(e.g. DatasetCollections, Histories, LibraryFolders)
"""
# Histories should be DatasetCollections.
# Libraries should be DatasetCollections.
import logging
import operator

import galaxy.exceptions
import galaxy.util
from galaxy import model

log = logging.getLogger(__name__)


# ====
class ContainerManagerMixin(object):
    """
    A class that tracks/contains two types of items:
        1) some non-container object (such as datasets)
        2) other sub-containers nested within this one

    Levels of nesting are not considered here; In other words,
    each of the methods below only work on the first level of
    nesting.
    """
    # TODO: terminology is getting a bit convoluted and silly at this point: rename three public below?
    # TODO: this should be an open mapping (not just 2)
    #: the classes that can be contained
    contained_class = None
    subcontainer_class = None
    #: how any contents lists produced are ordered - (string) attribute name to sort on or tuple of attribute names
    default_order_by = None

    # ---- interface
    def contents(self, container):
        """
        Returns both types of contents: filtered and in some order.
        """
        iters = []
        iters.append(self.contained(container))
        iters.append(self.subcontainers(container))
        return galaxy.util.merge_sorted_iterables(self.order_contents_on, *iters)

    def contained(self, container, **kwargs):
        """
        Returns non-container objects.
        """
        return self._filter_contents(container, self.contained_class, **kwargs)

    def subcontainers(self, container, **kwargs):
        """
        Returns only the containers within this one.
        """
        return self._filter_contents(container, self.subcontainer_class, **kwargs)

    # ---- private
    def _filter_contents(self, container, content_class, **kwargs):
        # TODO: use list (or by_history etc.)
        container_filter = self._filter_to_contained(container, content_class)
        query = self.session().query(content_class).filter(container_filter)
        return query

    def _get_filter_for_contained(self, container, content_class):
        raise galaxy.exceptions.NotImplemented('Abstract class')

    def _content_manager(self, content):
        raise galaxy.exceptions.NotImplemented('Abstract class')


class LibraryFolderAsContainerManagerMixin(ContainerManagerMixin):
    # can contain two types of subcontainer: LibraryFolder, LibraryDatasetCollectionAssociation
    # has as the top level container: Library

    contained_class = model.LibraryDataset
    subcontainer_class = model.LibraryFolder
    # subcontainer_class = model.LibraryDatasetCollectionAssociation
    order_contents_on = operator.attrgetter('create_time')

    def _get_filter_for_contained(self, container, content_class):
        if content_class == self.subcontainer_class:
            return self.subcontainer_class.parent == container
        return self.contained_class.folder == container

    def _content_manager(self, content):
        # type snifffing is inevitable
        if isinstance(content, model.LibraryDataset):
            return self.lda_manager
        elif isinstance(content, model.LibraryFolder):
            return self.folder_manager
        raise TypeError('Unknown contents class: ' + str(content))


class DatasetCollectionAsContainerManagerMixin(ContainerManagerMixin):

    # (note: unlike the other collections, dc's wrap both contained and subcontainers in this class)
    contained_class = model.DatasetCollectionElement
    subcontainer_class = model.DatasetCollection
    order_contents_on = operator.attrgetter('element_index')

    def _get_filter_for_contained(self, container, content_class):
        return content_class.collection == container

    def _content_manager(self, content):
        # type snifffing is inevitable
        if isinstance(content, model.DatasetCollectionElement):
            return self.collection_manager
        elif isinstance(content, model.DatasetCollection):
            return self.collection_manager
        raise TypeError('Unknown contents class: ' + str(content))
