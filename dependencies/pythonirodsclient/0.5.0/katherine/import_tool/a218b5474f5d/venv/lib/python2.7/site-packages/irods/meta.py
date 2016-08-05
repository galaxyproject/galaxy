class iRODSMeta(object):

    def __init__(self, name, value, units=None, id=None):
        self.id = id
        self.name = name
        self.value = value
        self.units = units

    def __repr__(self):
        return "<iRODSMeta {id} {name} {value} {units}>".format(**vars(self))


class iRODSMetaCollection(object):

    def __init__(self, manager, model_cls, path):
        self._manager = manager
        self._model_cls = model_cls
        self._path = path
        self._reset_metadata()

    def _reset_metadata(self):
        self._meta = self._manager.get(self._model_cls, self._path)

    def get_all(self, key):
        """
        Returns a list of iRODSMeta associated with a given key
        """
        if not isinstance(key, str):
            raise TypeError
        return [m for m in self._meta if m.name == key]

    def get_one(self, key):
        """
        Returns the iRODSMeta defined for a key. If there are none,
        or if there are more than one defined, raises KeyError
        """
        values = self.get_all(key)
        if not values:
            raise KeyError
        if len(values) > 1:
            raise KeyError
        return values[0]

    def _get_meta(self, *args):
        if not len(args):
            raise ValueError(
                "Must specify an iRODSMeta object or key, value, units)")
        return args[0] if len(args) == 1 else iRODSMeta(*args)

    def add(self, *args):
        """
        Add as iRODSMeta to a key
        """
        meta = self._get_meta(*args)
        self._manager.add(self._model_cls, self._path, meta)
        self._reset_metadata()

    def remove(self, *args):
        """
        Removes an iRODSMeta
        """
        meta = self._get_meta(*args)
        self._manager.remove(self._model_cls, self._path, meta)
        self._reset_metadata()

    def items(self):
        """
        Returns a list of iRODSMeta
        """
        return self._meta

    def keys(self):
        """
        Return a list of keys. Duplicates preserved
        """
        return [m.name for m in self._meta]

    def __len__(self):
        return len(self._meta)

    def __getitem__(self, key):
        """
        Returns the first iRODSMeta defined on key. Order is
        undefined. Use get_one() or get_all() instead
        """
        values = self.get_all(key)
        if not values:
            raise KeyError
        return values[0]

    def __setitem__(self, key, meta):
        """
        Deletes all existing values associated with a given key and associates
        the key with a single iRODSMeta tuple
        """
        self._delete_all_values(key)
        self.add(meta)

    def _delete_all_values(self, key):
        for meta in self.get_all(key):
            self.remove(meta)

    def __delitem__(self, key):
        """
        Deletes all existing values associated with a given key
        """
        if not isinstance(key, str):
            raise TypeError
        self._delete_all_values(key)
        self._reset_metadata()

    def __contains__(self, key):
        if not isinstance(key, str):
            raise TypeError
        values = self.get_all(key)
        return len(values) > 0

    def remove_all(self):
        for meta in self._meta:
            self._manager.remove(self._model_cls, self._path, meta)
        self._reset_metadata()
