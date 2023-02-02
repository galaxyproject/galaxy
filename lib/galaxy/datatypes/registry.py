"""
Provides mapping between extensions and datatypes, mime-types, etc.
"""

import importlib.util
import logging
import os
import pkgutil
from pathlib import Path
from string import Template
from typing import (
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import yaml

import galaxy.util
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.tool_util.edam_util import load_edam_tree
from galaxy.util import RW_R__R__
from galaxy.util.bunch import Bunch
from . import (
    binary,
    coverage,
    data,
    images,
    interval,
    qualityscore,
    sequence,
    tabular,
    text,
    tracks,
    xml,
)
from .display_applications.application import DisplayApplication


class ConfigurationError(Exception):
    pass


class Registry:
    def __init__(self, config=None):
        edam_ontology_path = config.get("edam_toolbox_ontology_path", None) if config is not None else None

        edam = load_edam_tree(
            None if not edam_ontology_path or not os.path.exists(edam_ontology_path) else edam_ontology_path,
            "format_",
            "data_",
            "operation_",
            "topic_",
        )

        self.log = logging.getLogger(__name__)
        self.log.addHandler(logging.NullHandler())
        self.config = config
        self.edam = edam
        self.datatypes_by_extension = {}
        self.datatypes_by_suffix_inferences = {}
        self.mimetypes_by_extension = {}
        self.datatype_converters = {}
        # Converters defined in local datatypes_conf.xml
        self.converters = []
        self.converter_tools = set()
        self.converter_deps = {}
        self.available_tracks = []
        self.set_external_metadata_tool = None
        self.sniff_order = []
        self.upload_file_formats = []
        # Datatype elements defined in local datatypes_conf.xml that contain display applications.
        self.display_app_containers = []
        # Map a display application id to a display application
        self.display_applications: Dict[str, DisplayApplication] = {}
        # The following 2 attributes are used in the to_xml_file()
        # method to persist the current state into an xml file.
        self.display_path_attr = None
        self.converters_path_attr = None
        # The 'default' converters_path defined in local datatypes_conf.xml
        self.converters_path = None
        # The 'default' display_path defined in local datatypes_conf.xml
        self.display_applications_path = None
        self.inherit_display_application_by_class = []
        self.datatype_elems = []
        self.datatype_info_dicts = []
        self.sniffer_elems = []
        self._registry_xml_string = None
        self._edam_formats_mapping = None
        self._edam_data_mapping = None
        self._converters_by_datatype = {}
        # Build sites
        self.build_sites = {}
        self.display_sites = {}
        self.legacy_build_sites = {}

    def load_datatypes(
        self,
        root_dir=None,
        config=None,
        override=True,
        use_converters=True,
        use_display_applications=True,
        use_build_sites=True,
    ):
        """
        Parse a datatypes XML file located at root_dir/config (if processing the Galaxy distributed config) or contained within
        an installed Tool Shed repository.
        """

        def __import_module(full_path: str, datatype_module: str):
            path_entry_finder = pkgutil.get_importer(full_path)
            assert path_entry_finder, "path_entry_finder is None"
            spec = path_entry_finder.find_spec(datatype_module)
            assert spec, "spec is None"
            module = importlib.util.module_from_spec(spec)
            assert spec.loader, "spec.loader is None"
            spec.loader.exec_module(module)
            return module

        if root_dir and config:
            compressed_sniffers = {}
            if isinstance(config, (str, Path)):
                # Parse datatypes_conf.xml
                tree = galaxy.util.parse_xml(config)
                root = tree.getroot()
                # Load datatypes and converters from config
                self.log.debug(f"Loading datatypes from {config}")
            else:
                root = config
            registration = root.find("registration")
            # Set default paths defined in local datatypes_conf.xml.
            if use_converters:
                if not self.converters_path:
                    self.converters_path_attr = registration.get("converters_path", "lib/galaxy/datatypes/converters")
                    self.converters_path = os.path.join(root_dir, self.converters_path_attr)
                    if self.converters_path_attr == "lib/galaxy/datatypes/converters" and not os.path.isdir(
                        self.converters_path
                    ):
                        # Deal with the old default of this path being set in
                        # datatypes_conf.xml.sample (this path is not useful in an
                        # "installed Galaxy" world)
                        self.converters_path_attr = os.path.abspath(
                            os.path.join(os.path.dirname(__file__), "converters")
                        )
                        self.converters_path = self.converters_path_attr
                    if not os.path.isdir(self.converters_path):
                        raise ConfigurationError(f"Directory does not exist: {self.converters_path}")
            if use_display_applications:
                if not self.display_applications_path:
                    self.display_path_attr = registration.get("display_path", "display_applications")
                    self.display_applications_path = os.path.join(root_dir, self.display_path_attr)
                    if self.display_path_attr == "display_applications" and not os.path.isdir("display_applications"):
                        # Ditto as with converters_path
                        self.display_path_attr = os.path.abspath(
                            os.path.join(os.path.dirname(__file__), "display_applications", "configs")
                        )
                        self.display_applications_path = self.display_path_attr

            for elem in registration.findall("datatype"):
                # Keep a status of the process steps to enable stopping the process of handling the datatype if necessary.
                ok = True
                extension = self.get_extension(elem)
                dtype = elem.get("type", None)
                type_extension = elem.get("type_extension", None)
                auto_compressed_types = galaxy.util.listify(elem.get("auto_compressed_types", ""))
                sniff_compressed_types = galaxy.util.string_as_bool_or_none(elem.get("sniff_compressed_types", "None"))
                if sniff_compressed_types is None:
                    sniff_compressed_types = getattr(self.config, "sniff_compressed_dynamic_datatypes_default", True)
                    # Make sure this is set in the elems we write out so the config option is passed to the upload
                    # tool which does not have a config object.
                    elem.set("sniff_compressed_types", str(sniff_compressed_types))
                mimetype = elem.get("mimetype", None)
                display_in_upload = galaxy.util.string_as_bool(elem.get("display_in_upload", False))
                # If make_subclass is True, it does not necessarily imply that we are subclassing a datatype that is contained
                # in the distribution.
                make_subclass = galaxy.util.string_as_bool(elem.get("subclass", False))
                edam_format = elem.get("edam_format", None)
                if edam_format and not make_subclass:
                    self.log.warning("Cannot specify edam_format without setting subclass to True, skipping datatype.")
                    continue
                edam_data = elem.get("edam_data", None)
                if edam_data and not make_subclass:
                    self.log.warning("Cannot specify edam_data without setting subclass to True, skipping datatype.")
                    continue

                # We are loading new datatype, so we'll make sure it is correctly defined before proceeding.
                can_process_datatype = False
                if extension is not None:
                    if dtype is not None or type_extension is not None:
                        if override or extension not in self.datatypes_by_extension:
                            can_process_datatype = True
                if can_process_datatype:
                    if dtype is not None:
                        try:
                            fields = dtype.split(":")
                            datatype_module = fields[0]
                            datatype_class_name = fields[1]
                        except Exception:
                            self.log.exception("Error parsing datatype definition for dtype %s", str(dtype))
                            ok = False
                        if ok:
                            datatype_class = None
                            if datatype_class is None:
                                try:
                                    # The datatype class name must be contained in one of the datatype modules in the Galaxy distribution.
                                    fields = datatype_module.split(".")[1:]
                                    module = __import__(datatype_module)
                                    for mod in fields:
                                        module = getattr(module, mod)
                                    datatype_class = getattr(module, datatype_class_name)
                                    self.log.debug(
                                        f"Retrieved datatype module {str(datatype_module)}:{datatype_class_name} from the datatype registry for extension {extension}."
                                    )
                                except Exception:
                                    self.log.exception("Error importing datatype module %s", str(datatype_module))
                                    ok = False
                    elif type_extension is not None:
                        try:
                            datatype_class = self.datatypes_by_extension[type_extension].__class__
                            self.log.debug(
                                f"Retrieved datatype module {str(datatype_class.__name__)} from type_extension {type_extension} for extension {extension}."
                            )
                        except Exception:
                            self.log.exception(
                                "Error determining datatype_class for type_extension %s", str(type_extension)
                            )
                            ok = False
                    if ok:
                        # A new tool shed repository that contains custom datatypes is being installed, and since installation is
                        # occurring after the datatypes registry has been initialized at server startup, its contents cannot be
                        # overridden by new introduced conflicting data types unless the value of override is True.
                        if extension in self.datatypes_by_extension:
                            # Because of the way that the value of can_process_datatype was set above, we know that the value of
                            # override is True.
                            self.log.debug(
                                "Overriding conflicting datatype with extension '%s', using datatype from %s."
                                % (str(extension), str(config))
                            )
                        if make_subclass:
                            datatype_class = type(datatype_class_name, (datatype_class,), {})
                            if edam_format:
                                datatype_class.edam_format = edam_format
                            if edam_data:
                                datatype_class.edam_data = edam_data
                        datatype_class.is_subclass = make_subclass
                        description = elem.get("description", None)
                        description_url = elem.get("description_url", None)
                        datatype_instance = datatype_class()
                        self.datatypes_by_extension[extension] = datatype_instance
                        if mimetype is None:
                            # Use default mimetype per datatype specification.
                            mimetype = self.datatypes_by_extension[extension].get_mime()
                        self.mimetypes_by_extension[extension] = mimetype
                        if datatype_class.track_type:
                            self.available_tracks.append(extension)
                        if display_in_upload and extension not in self.upload_file_formats:
                            self.upload_file_formats.append(extension)
                        # Max file size cut off for setting optional metadata.
                        self.datatypes_by_extension[extension].max_optional_metadata_filesize = elem.get(
                            "max_optional_metadata_filesize", None
                        )
                        infer_from_suffixes = []
                        # read from element instead of attribute so we can customize references to
                        # compressed files in the future (e.g. maybe some day faz will be a compressed fasta
                        # or something along those lines)
                        for infer_from in elem.findall("infer_from"):
                            suffix = infer_from.get("suffix", None)
                            if suffix is None:
                                raise Exception("Failed to parse infer_from datatype element")
                            infer_from_suffixes.append(suffix)
                            self.datatypes_by_suffix_inferences[suffix] = datatype_instance
                        for converter in elem.findall("converter"):
                            # Build the list of datatype converters which will later be loaded into the calling app's toolbox.
                            converter_config = converter.get("file", None)
                            target_datatype = converter.get("target_datatype", None)
                            depends_on = converter.get("depends_on", None)
                            if depends_on is not None and target_datatype is not None:
                                if extension not in self.converter_deps:
                                    self.converter_deps[extension] = {}
                                self.converter_deps[extension][target_datatype] = depends_on.split(",")
                            if converter_config and target_datatype:
                                self.converters.append((converter_config, extension, target_datatype))
                        # Add composite files.
                        for composite_file in elem.findall("composite_file"):
                            name = composite_file.get("name", None)
                            if name is None:
                                self.log.warning(f"You must provide a name for your composite_file ({composite_file}).")
                            optional = composite_file.get("optional", False)
                            mimetype = composite_file.get("mimetype", None)
                            self.datatypes_by_extension[extension].add_composite_file(
                                name, optional=optional, mimetype=mimetype
                            )
                        for _display_app in elem.findall("display"):
                            if elem not in self.display_app_containers:
                                self.display_app_containers.append(elem)
                        datatype_info_dict = {
                            "display_in_upload": display_in_upload,
                            "extension": extension,
                            "description": description,
                            "description_url": description_url,
                        }
                        composite_files = datatype_instance.get_composite_files()
                        if composite_files:
                            _composite_files = []
                            for name, composite_file in composite_files.items():
                                _composite_file = composite_file.dict()
                                _composite_file["name"] = name
                                _composite_files.append(_composite_file)
                            datatype_info_dict["composite_files"] = _composite_files
                        self.datatype_info_dicts.append(datatype_info_dict)

                        for auto_compressed_type in auto_compressed_types:
                            compressed_extension = f"{extension}.{auto_compressed_type}"
                            upper_compressed_type = auto_compressed_type[0].upper() + auto_compressed_type[1:]
                            auto_compressed_type_name = datatype_class_name + upper_compressed_type
                            attributes = {}
                            if auto_compressed_type == "gz":
                                dynamic_parent = binary.GzDynamicCompressedArchive
                            elif auto_compressed_type == "bz2":
                                dynamic_parent = binary.Bz2DynamicCompressedArchive
                            else:
                                raise Exception(f"Unknown auto compression type [{auto_compressed_type}]")
                            attributes["file_ext"] = compressed_extension
                            attributes["uncompressed_datatype_instance"] = datatype_instance
                            compressed_datatype_class = type(
                                auto_compressed_type_name,
                                (
                                    datatype_class,
                                    dynamic_parent,
                                ),
                                attributes,
                            )
                            if edam_format:
                                compressed_datatype_class.edam_format = edam_format
                            if edam_data:
                                compressed_datatype_class.edam_data = edam_data
                            compressed_datatype_instance = compressed_datatype_class()
                            self.datatypes_by_extension[compressed_extension] = compressed_datatype_instance
                            for suffix in infer_from_suffixes:
                                self.datatypes_by_suffix_inferences[
                                    f"{suffix}.{auto_compressed_type}"
                                ] = compressed_datatype_instance
                            if display_in_upload and compressed_extension not in self.upload_file_formats:
                                self.upload_file_formats.append(compressed_extension)
                            self.datatype_info_dicts.append(
                                {
                                    "display_in_upload": display_in_upload,
                                    "extension": compressed_extension,
                                    "description": description,
                                    "description_url": description_url,
                                }
                            )
                            if auto_compressed_type == "gz":
                                self.converters.append(
                                    (
                                        f"uncompressed_to_{auto_compressed_type}.xml",
                                        extension,
                                        compressed_extension,
                                    )
                                )
                            self.converters.append(
                                (f"{auto_compressed_type}_to_uncompressed.xml", compressed_extension, extension)
                            )
                            if datatype_class not in compressed_sniffers:
                                compressed_sniffers[datatype_class] = []
                            if sniff_compressed_types:
                                compressed_sniffers[datatype_class].append(compressed_datatype_instance)
                        # Processing the new datatype elem is now complete, so make sure the element defining it is retained by appending
                        # the new datatype to the in-memory list of datatype elems to enable persistence.
                        self.datatype_elems.append(elem)
                    else:
                        if extension is not None:
                            if dtype is not None or type_extension is not None:
                                if extension in self.datatypes_by_extension:
                                    if not override:
                                        # Do not load the datatype since it conflicts with an existing datatype which we are not supposed
                                        # to override.
                                        self.log.debug(
                                            f"Ignoring conflicting datatype with extension '{extension}' from {config}."
                                        )
            # Load datatype sniffers from the config - we'll do this even if one or more datatypes were not properly processed in the config
            # since sniffers are not tightly coupled with datatypes.
            self.load_datatype_sniffers(
                root,
                override=override,
                compressed_sniffers=compressed_sniffers,
            )
            self.upload_file_formats.sort()
            # Load build sites
            if use_build_sites:
                self._load_build_sites(root)
        self.set_default_values()

        def append_to_sniff_order():
            sniff_order_classes = {type(_) for _ in self.sniff_order}
            for datatype in self.datatypes_by_extension.values():
                # Add a datatype only if it is not already in sniff_order, it
                # has a sniff() method and was not defined with subclass="true".
                # Do not add dynamic compressed types - these were carefully added or not
                # to the sniff order in the proper position above.
                if (
                    type(datatype) not in sniff_order_classes
                    and hasattr(datatype, "sniff")
                    and not datatype.is_subclass
                    and not hasattr(datatype, "uncompressed_datatype_instance")
                ):
                    self.sniff_order.append(datatype)

        append_to_sniff_order()

    def _load_build_sites(self, root):
        def load_build_site(build_site_config):
            # Take in either an XML element or simple dictionary from YAML and add build site for this.
            if not (build_site_config.get("type") and build_site_config.get("file")):
                self.log.exception("Site is missing required 'type' and 'file' attributes")
                return

            site_type = build_site_config.get("type")
            path = build_site_config.get("file")
            if not os.path.exists(path):
                sample_path = f"{path}.sample"
                if os.path.exists(sample_path):
                    self.log.debug(f"Build site file [{path}] not found using sample [{sample_path}].")
                    path = sample_path

            self.build_sites[site_type] = path
            if site_type in ("ucsc", "gbrowse"):
                self.legacy_build_sites[site_type] = galaxy.util.read_build_sites(path)
            if build_site_config.get("display", None):
                display = build_site_config.get("display")
                if not isinstance(display, list):
                    display = [x.strip() for x in display.lower().split(",")]
                self.display_sites[site_type] = display
                self.log.debug("Loaded build site '%s': %s with display sites: %s", site_type, path, display)
            else:
                self.log.debug("Loaded build site '%s': %s", site_type, path)

        if root.find("build_sites") is not None:
            for elem in root.find("build_sites").findall("site"):
                load_build_site(elem)
        else:
            build_sites_config_file = getattr(self.config, "build_sites_config_file", None)
            if build_sites_config_file and os.path.exists(build_sites_config_file):
                with open(build_sites_config_file) as f:
                    build_sites_config = yaml.safe_load(f)
                if not isinstance(build_sites_config, list):
                    self.log.exception("Build sites configuration YAML file does not declare list of sites.")
                    return

                for build_site_config in build_sites_config:
                    load_build_site(build_site_config)
            else:
                self.log.debug("No build sites source located.")

    def get_legacy_sites_by_build(self, site_type, build):
        sites = []
        for site in self.legacy_build_sites.get(site_type, []):
            if build in site["builds"]:
                sites.append((site["name"], site["url"]))
        return sites

    def get_display_sites(self, site_type):
        return self.display_sites.get(site_type, [])

    def load_datatype_sniffers(self, root, override=False, compressed_sniffers=None):
        """
        Process the sniffers element from a parsed a datatypes XML file located at root_dir/config (if processing the Galaxy
        distributed config) or contained within an installed Tool Shed repository.
        """
        sniffer_elem_classes = [e.attrib["type"] for e in self.sniffer_elems]
        sniffers = root.find("sniffers")
        if sniffers is not None:
            for elem in sniffers.findall("sniffer"):
                # Keep a status of the process steps to enable stopping the process of handling the sniffer if necessary.
                ok = True
                dtype = elem.get("type", None)
                if dtype is not None:
                    try:
                        fields = dtype.split(":")
                        datatype_module = fields[0]
                        datatype_class_name = fields[1]
                        module = None
                    except Exception:
                        self.log.exception("Error determining datatype class or module for dtype %s", str(dtype))
                        ok = False
                    if ok:
                        if module is None:
                            try:
                                # The datatype class name must be contained in one of the datatype modules in the Galaxy distribution.
                                module = __import__(datatype_module)
                                for comp in datatype_module.split(".")[1:]:
                                    module = getattr(module, comp)
                            except Exception:
                                self.log.exception("Error importing datatype class for '%s'", str(dtype))
                                ok = False
                        if ok:
                            try:
                                aclass = getattr(module, datatype_class_name)()
                            except Exception:
                                self.log.exception(
                                    "Error calling method %s from class %s", str(datatype_class_name), str(module)
                                )
                                ok = False
                            if ok:
                                # We are loading new sniffer, so see if we have a conflicting sniffer already loaded.
                                conflict = False
                                for conflict_loc, sniffer_class in enumerate(self.sniff_order):
                                    if sniffer_class.__class__ == aclass.__class__:
                                        # We have a conflicting sniffer, so replace the one previously loaded.
                                        conflict = True
                                        if override:
                                            del self.sniff_order[conflict_loc]
                                            self.log.debug(f"Removed conflicting sniffer for datatype '{dtype}'")
                                        break
                                if not conflict or override:
                                    if compressed_sniffers and aclass.__class__ in compressed_sniffers:
                                        for compressed_sniffer in compressed_sniffers[aclass.__class__]:
                                            self.sniff_order.append(compressed_sniffer)
                                    self.sniff_order.append(aclass)
                                    self.log.debug(f"Loaded sniffer for datatype '{dtype}'")
                                # Processing the new sniffer elem is now complete, so make sure the element defining it is loaded if necessary.
                                sniffer_class = elem.get("type", None)
                                if sniffer_class is not None:
                                    if sniffer_class not in sniffer_elem_classes:
                                        self.sniffer_elems.append(elem)

    def get_datatype_from_filename(self, name):
        max_extension_parts = 3
        generic_datatype_instance = self.get_datatype_by_extension("data")
        if "." not in name:
            return generic_datatype_instance
        extension_parts = name.rsplit(".", max_extension_parts)[1:]
        possible_extensions = []
        for n, _ in enumerate(extension_parts):
            possible_extensions.append(".".join(extension_parts[n:]))

        infer_from = self.datatypes_by_suffix_inferences
        for possible_extension in possible_extensions:
            if possible_extension in infer_from:
                return infer_from[possible_extension]

        for possible_extension in possible_extensions:
            if possible_extension in self.datatypes_by_extension:
                return self.datatypes_by_extension[possible_extension]

        return generic_datatype_instance

    def is_extension_unsniffable_binary(self, ext):
        datatype = self.get_datatype_by_extension(ext)
        return datatype is not None and isinstance(datatype, binary.Binary) and not hasattr(datatype, "sniff")

    def get_datatype_class_by_name(self, name):
        """
        Return the datatype class where the datatype's `type` attribute
        (as defined in the datatype_conf.xml file) contains `name`.
        """
        # TODO: obviously not ideal but some of these base classes that are useful for testing datatypes
        # aren't loaded into the datatypes registry, so we'd need to test for them here
        if name == "images.Image":
            return images.Image

        # TODO: too inefficient - would be better to generate this once as a map and store in this object
        for datatype_obj in self.datatypes_by_extension.values():
            datatype_obj_class = datatype_obj.__class__
            datatype_obj_class_str = str(datatype_obj_class)
            if name in datatype_obj_class_str:
                return datatype_obj_class
        return None

    def get_available_tracks(self):
        return self.available_tracks

    def get_mimetype_by_extension(self, ext, default="application/octet-stream"):
        """Returns a mimetype based on an extension"""
        try:
            mimetype = self.mimetypes_by_extension[ext]
        except KeyError:
            # datatype was never declared
            mimetype = default
            self.log.warning(f"unknown mimetype in data factory {str(ext)}")
        return mimetype

    def get_datatype_by_extension(self, ext):
        """Returns a datatype object based on an extension"""
        return self.datatypes_by_extension.get(ext, None)

    def change_datatype(self, data, ext):
        data.extension = ext
        # call init_meta and copy metadata from itself.  The datatype
        # being converted *to* will handle any metadata copying and
        # initialization.
        if data.has_data():
            data.set_size()
            data.init_meta(copy_from=data)
        return data

    def load_datatype_converters(self, toolbox, use_cached=False):
        """
        Add datatype converters from self.converters to the calling app's toolbox.
        """
        # Load converters defined by local datatypes_conf.xml.
        converters = self.converters
        for elem in converters:
            tool_config = elem[0]
            source_datatype = elem[1]
            target_datatype = elem[2]
            converter_path = self.converters_path
            try:
                config_path = os.path.join(converter_path, tool_config)
                converter = toolbox.load_tool(config_path, use_cached=use_cached)
                self.converter_tools.add(converter)
                toolbox.register_tool(converter)
                if source_datatype not in self.datatype_converters:
                    self.datatype_converters[source_datatype] = {}
                self.datatype_converters[source_datatype][target_datatype] = converter
                if not hasattr(toolbox.app, "tool_cache") or converter.id in toolbox.app.tool_cache._new_tool_ids:
                    self.log.debug("Loaded converter: %s", converter.id)
            except Exception:
                self.log.exception(f"Error loading converter ({converter_path})")

    def load_display_applications(self, app):
        """
        Add display applications from self.display_app_containers or to appropriate datatypes.
        """
        # Load display applications defined by local datatypes_conf.xml.
        datatype_elems = self.display_app_containers
        for elem in datatype_elems:
            extension = self.get_extension(elem)
            for display_app in elem.findall("display"):
                display_file = display_app.get("file", None)
                config_path = os.path.join(self.display_applications_path, display_file)
                try:
                    inherit = galaxy.util.string_as_bool(display_app.get("inherit", "False"))
                    display_app = DisplayApplication.from_file(config_path, app)
                    if display_app:
                        if display_app.id in self.display_applications:
                            # If we already loaded this display application, we'll use the first one loaded.
                            display_app = self.display_applications[display_app.id]

                        self.display_applications[display_app.id] = display_app
                        self.datatypes_by_extension[extension].add_display_application(display_app)
                        if (
                            inherit
                            and (self.datatypes_by_extension[extension], display_app)
                            not in self.inherit_display_application_by_class
                        ):
                            self.inherit_display_application_by_class.append(
                                (self.datatypes_by_extension[extension], display_app)
                            )
                        self.log.debug(
                            f"Loaded display application '{display_app.id}' for datatype '{extension}', inherit={inherit}."
                        )
                except Exception:
                    self.log.exception(f"Error loading display application ({config_path})")
        # Handle display_application subclass inheritance.
        for extension, d_type1 in self.datatypes_by_extension.items():
            for d_type2, display_app in self.inherit_display_application_by_class:
                current_app = d_type1.get_display_application(display_app.id, None)
                if current_app is None and isinstance(d_type1, type(d_type2)):
                    self.log.debug(f"Adding inherited display application '{display_app.id}' to datatype '{extension}'")
                    d_type1.add_display_application(display_app)

    def reload_display_applications(self, display_application_ids=None):
        """
        Reloads display applications: by id, or all if no ids provided
        Returns tuple( [reloaded_ids], [failed_ids] )
        """
        if not display_application_ids:
            display_application_ids = self.display_applications.keys()
        elif not isinstance(display_application_ids, list):
            display_application_ids = [display_application_ids]
        reloaded = []
        failed = []
        for display_application_id in display_application_ids:
            try:
                self.display_applications[display_application_id].reload()
                reloaded.append(display_application_id)
            except Exception as e:
                self.log.debug(
                    'Requested to reload display application "%s", but failed: %s.', display_application_id, e
                )
                failed.append(display_application_id)
        return (reloaded, failed)

    def load_external_metadata_tool(self, toolbox):
        """Adds a tool which is used to set external metadata"""
        # We need to be able to add a job to the queue to set metadata. The queue will currently only accept jobs with an associated
        # tool.  We'll load a special tool to be used for Auto-Detecting metadata; this is less than ideal, but effective
        # Properly building a tool without relying on parsing an XML file is near difficult...so we bundle with Galaxy.
        set_meta_tool = toolbox.load_hidden_lib_tool(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "set_metadata_tool.xml"))
        )
        self.set_external_metadata_tool = set_meta_tool
        self.log.debug("Loaded external metadata tool: %s", self.set_external_metadata_tool.id)

    def set_default_values(self):
        # Default values.
        if not self.datatypes_by_extension:
            self.datatypes_by_extension = {
                "ab1": binary.Ab1(),
                "axt": sequence.Axt(),
                "bam": binary.Bam(),
                "jp2": binary.JP2(),
                "bed": interval.Bed(),
                "coverage": coverage.LastzCoverage(),
                "customtrack": interval.CustomTrack(),
                "csfasta": sequence.csFasta(),
                "fasta": sequence.Fasta(),
                "eland": tabular.Eland(),
                "fastq": sequence.Fastq(),
                "fastqsanger": sequence.FastqSanger(),
                "gtf": interval.Gtf(),
                "gff": interval.Gff(),
                "gff3": interval.Gff3(),
                "genetrack": tracks.GeneTrack(),
                "h5": binary.H5(),
                "interval": interval.Interval(),
                "laj": images.Laj(),
                "lav": sequence.Lav(),
                "maf": sequence.Maf(),
                "pileup": tabular.Pileup(),
                "qualsolid": qualityscore.QualityScoreSOLiD(),
                "qualsolexa": qualityscore.QualityScoreSolexa(),
                "qual454": qualityscore.QualityScore454(),
                "sam": tabular.Sam(),
                "scf": binary.Scf(),
                "sff": binary.Sff(),
                "tabular": tabular.Tabular(),
                "csv": tabular.CSV(),
                "taxonomy": tabular.Taxonomy(),
                "txt": data.Text(),
                "wig": interval.Wiggle(),
                "xml": xml.GenericXml(),
            }
            self.mimetypes_by_extension = {
                "ab1": "application/octet-stream",
                "axt": "text/plain",
                "bam": "application/octet-stream",
                "jp2": "application/octet-stream",
                "bed": "text/plain",
                "customtrack": "text/plain",
                "csfasta": "text/plain",
                "eland": "application/octet-stream",
                "fasta": "text/plain",
                "fastq": "text/plain",
                "fastqsanger": "text/plain",
                "gtf": "text/plain",
                "gff": "text/plain",
                "gff3": "text/plain",
                "h5": "application/octet-stream",
                "interval": "text/plain",
                "laj": "text/plain",
                "lav": "text/plain",
                "maf": "text/plain",
                "memexml": "application/xml",
                "pileup": "text/plain",
                "qualsolid": "text/plain",
                "qualsolexa": "text/plain",
                "qual454": "text/plain",
                "sam": "text/plain",
                "scf": "application/octet-stream",
                "sff": "application/octet-stream",
                "tabular": "text/plain",
                "csv": "text/plain",
                "taxonomy": "text/plain",
                "txt": "text/plain",
                "wig": "text/plain",
                "xml": "application/xml",
            }
        # super supertype fix for input steps in workflows.
        if "data" not in self.datatypes_by_extension:
            self.datatypes_by_extension["data"] = data.Data()
            self.mimetypes_by_extension["data"] = "application/octet-stream"
        # Default values - the order in which we attempt to determine data types is critical
        # because some formats are much more flexibly defined than others.
        if len(self.sniff_order) < 1:
            self.sniff_order = [
                binary.Bam(),
                binary.Sff(),
                binary.JP2(),
                binary.H5(),
                xml.GenericXml(),
                sequence.Maf(),
                sequence.Lav(),
                sequence.csFasta(),
                qualityscore.QualityScoreSOLiD(),
                qualityscore.QualityScore454(),
                sequence.Fasta(),
                sequence.FastqSanger(),
                sequence.FastqCSSanger(),
                sequence.Fastq(),
                interval.Wiggle(),
                text.Html(),
                sequence.Axt(),
                interval.Bed(),
                interval.CustomTrack(),
                interval.Gtf(),
                interval.Gff(),
                interval.Gff3(),
                tabular.Pileup(),
                interval.Interval(),
                tabular.Sam(),
                tabular.Eland(),
                tabular.CSV(),
            ]

    def get_converters_by_datatype(self, ext):
        """Returns available converters by source type"""
        if ext not in self._converters_by_datatype:
            converters = {}
            source_datatype = type(self.get_datatype_by_extension(ext))
            for ext2, converters_dict in self.datatype_converters.items():
                converter_datatype = type(self.get_datatype_by_extension(ext2))
                if issubclass(source_datatype, converter_datatype):
                    converters.update({k: v for k, v in converters_dict.items() if k != ext})
            # Ensure ext-level converters are present
            if ext in self.datatype_converters.keys():
                converters.update(self.datatype_converters[ext])
            self._converters_by_datatype[ext] = converters
        return self._converters_by_datatype[ext]

    def get_converter_by_target_type(self, source_ext, target_ext):
        """Returns a converter based on source and target datatypes"""
        converters = self.get_converters_by_datatype(source_ext)
        if target_ext in converters.keys():
            return converters[target_ext]
        return None

    def find_conversion_destination_for_dataset_by_extensions(
        self, dataset_or_ext: Union[str, DatasetProtocol], accepted_formats: List[str], converter_safe: bool = True
    ) -> Tuple[bool, Optional[str], Optional[DatasetProtocol]]:
        """
        returns (direct_match, converted_ext, converted_dataset)
        - direct match is True iff no the data set already has an accepted format
        - target_ext becomes None if conversion is not possible (or necesary)
        """
        if hasattr(dataset_or_ext, "ext"):
            ext = dataset_or_ext.ext
            dataset = cast(DatasetProtocol, dataset_or_ext)
        else:
            ext = dataset_or_ext
            dataset = None

        datatype_by_extension = self.get_datatype_by_extension(ext)
        if datatype_by_extension and datatype_by_extension.matches_any(accepted_formats):
            return True, None, None

        for convert_ext in self.get_converters_by_datatype(ext):
            convert_ext_datatype = self.get_datatype_by_extension(convert_ext)
            if convert_ext_datatype is None:
                self.log.warning(
                    f"Datatype class not found for extension '{convert_ext}', which is used as target for conversion from datatype '{ext}'"
                )
            elif convert_ext_datatype.matches_any(accepted_formats):
                converted_dataset = dataset and dataset.get_converted_files_by_type(convert_ext)
                if converted_dataset:
                    ret_data = converted_dataset
                elif not converter_safe:
                    continue
                else:
                    ret_data = None
                return False, convert_ext, ret_data
        return False, None, None

    def get_composite_extensions(self):
        return [ext for (ext, d_type) in self.datatypes_by_extension.items() if d_type.composite_type is not None]

    def get_upload_metadata_params(self, context, group, tool):
        """Returns dict of case value:inputs for metadata conditional for upload tool"""
        rval = {}
        for ext, d_type in self.datatypes_by_extension.items():
            inputs = []
            for meta_name, meta_spec in d_type.metadata_spec.items():
                if meta_spec.set_in_upload:
                    help_txt = meta_spec.desc
                    if not help_txt or help_txt == meta_name:
                        help_txt = ""
                    inputs.append(
                        f'<param type="text" name="{meta_name}" label="Set metadata value for &quot;{meta_name}&quot;" value="{meta_spec.default}" help="{help_txt}"/>'
                    )
            rval[ext] = "\n".join(inputs)
        if "auto" not in rval and "txt" in rval:  # need to manually add 'auto' datatype
            rval["auto"] = rval["txt"]
        return rval

    @property
    def edam_formats(self):
        """ """
        if not self._edam_formats_mapping:
            self._edam_formats_mapping = {k: v.edam_format for k, v in self.datatypes_by_extension.items()}
        return self._edam_formats_mapping

    @property
    def edam_data(self):
        """ """
        if not self._edam_data_mapping:
            self._edam_data_mapping = {k: v.edam_data for k, v in self.datatypes_by_extension.items()}
        return self._edam_data_mapping

    def to_xml_file(self, path):
        if not self._registry_xml_string:
            registry_string_template = Template(
                """<?xml version="1.0"?>
            <datatypes>
              <registration converters_path="$converters_path" display_path="$display_path">
                $datatype_elems
              </registration>
              <sniffers>
                $sniffer_elems
              </sniffers>
            </datatypes>
            """
            )
            converters_path = self.converters_path_attr or ""
            display_path = self.display_path_attr or ""
            datatype_elems = "".join(galaxy.util.xml_to_string(elem) for elem in self.datatype_elems)
            sniffer_elems = "".join(galaxy.util.xml_to_string(elem) for elem in self.sniffer_elems)
            self._registry_xml_string = registry_string_template.substitute(
                converters_path=converters_path,
                display_path=display_path,
                datatype_elems=datatype_elems,
                sniffer_elems=sniffer_elems,
            )
        with open(os.path.abspath(path), "w") as registry_xml:
            os.chmod(path, RW_R__R__)
            registry_xml.write(self._registry_xml_string)

    def get_extension(self, elem):
        """
        Function which returns the extension lowercased
        :param elem:
        :return extension:
        """
        extension = elem.get("extension", None)
        # If extension is not None and is uppercase or mixed case, we need to lowercase it
        if extension is not None and not extension.islower():
            self.log.debug(
                "%s is not lower case, that could cause troubles in the future. \
            Please change it to lower case"
                % extension
            )
            extension = extension.lower()
        return extension

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle xml elements
        unpickleable_attributes = [
            "converter_tools",
            "datatype_converters",
            "datatype_elems",
            "display_app_containers",
            "display_applications",
            "inherit_display_application_by_class",
            "set_external_metadata_tool",
            "sniffer_elems",
        ]
        for unpicklable in unpickleable_attributes:
            state[unpicklable] = []
        return state


def example_datatype_registry_for_sample(sniff_compressed_dynamic_datatypes_default=True):
    galaxy_dir = galaxy.util.galaxy_directory()
    sample_conf = os.path.join(galaxy_dir, "lib", "galaxy", "config", "sample", "datatypes_conf.xml.sample")
    config = Bunch(sniff_compressed_dynamic_datatypes_default=sniff_compressed_dynamic_datatypes_default)
    datatypes_registry = Registry(config)
    datatypes_registry.load_datatypes(root_dir=galaxy_dir, config=sample_conf)
    return datatypes_registry
