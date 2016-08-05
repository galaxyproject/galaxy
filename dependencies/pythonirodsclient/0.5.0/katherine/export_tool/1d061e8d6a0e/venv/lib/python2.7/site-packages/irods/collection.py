import itertools
import operator
from os.path import basename

from irods.models import Collection, DataObject
from irods.data_object import iRODSDataObject
from irods.meta import iRODSMetaCollection

class iRODSCollection(object):
    def __init__(self, manager, result=None):
        self.manager = manager
        if result:
            self.id = result[Collection.id]
            self.path = result[Collection.name]
            self.name = basename(result[Collection.name])
        self._meta = None

    @property
    def metadata(self):
        if not self._meta:
            self._meta = iRODSMetaCollection(self.manager.sess.metadata, 
                Collection, self.path)
        return self._meta

    @property
    def subcollections(self):
        query = self.manager.sess.query(Collection)\
            .filter(Collection.parent_name == self.path)
        results = query.get_results()
        return [iRODSCollection(self.manager, row) for row in results]

    @property
    def data_objects(self):
        query = self.manager.sess.query(DataObject)\
            .filter(DataObject.collection_id == self.id)
        results = query.get_results()
        grouped = itertools.groupby(results, operator.itemgetter(DataObject.id))
        return [
            iRODSDataObject(self.manager.sess.data_objects, self, list(replicas))
            for _, replicas in grouped
        ]

    def remove(self, recurse=True, force=False, additional_flags={}):
        self.manager.remove(self.path, recurse, force, additional_flags)
        
    def move(self, path):
        self.manager.move(self.path, path)

    def walk(self, topdown=True):
        """
        Collection tree generator.
        
        For each subcollection in the directory tree, starting at the
        collection, yield a 3-tuple
        """

        if topdown:
            yield (self, self.subcollections, self.data_objects)
        for subcollection in self.subcollections:
            new_root = subcollection
            for x in new_root.walk(topdown):
                yield x
        if not topdown:
            yield (self, self.subcollections, self.data_objects)

    def __repr__(self):
        return "<iRODSCollection {id} {name}>".format(id=self.id, name=self.name.encode('utf-8'))
