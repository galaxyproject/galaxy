from __future__ import print_function

import argparse
import collections
import copy
import json
import logging
import os
import re
import sys
from functools import reduce
from xml.etree import ElementTree as ET

import numpy as np
from yaml import load

__version__ = '1.1.0'

# log to galaxy's logger
log = logging.getLogger(__name__)

# does a lot more logging when set to true
verbose = True

"""
list of all valid priorities, inferred from the global
default_desinations section of the config
"""
priority_list = set()

"""
Instantiated to a list of all valid destinations in the job configuration file
if run directly to validate configs. Otherwise, remains None. We often check
to see if app is None, because if it is then we'll try using the
destination_list instead.
-"""
destination_list = set()

"""
The largest the edit distance can be for a word to be considered
A correction for another word.
"""
max_edit_dist = 2

"""
List of valid categories that can be expected in the configuration.
"""
valid_categories = ['verbose', 'tools', 'default_destination',
                    'users', 'default_priority']

# --- destination validation error messages --- #
dest_err_default_dest = "Default destination '%s' does not appear in the job configuration."  # destination
dest_err_tool_default_dest = "Default destination for '%s': '%s' does not appear in the job configuration."  # tool, destination
dest_err_tool_rule_dest = "Destination for '%s', rule %s: '%s' does not exist in job configuration."  # tool, counter, destination


class MalformedYMLException(Exception):
    pass


class ScannerError(Exception):
    pass


def get_keys_from_dict(dl, keys_list):
    """
    This function builds a list using the keys from nest dictionaries
    """
    if isinstance(dl, dict):
        keys_list += dl.keys()
        map(lambda x: get_keys_from_dict(x, keys_list), dl.values())
    elif isinstance(dl, list):
        map(lambda x: get_keys_from_dict(x, keys_list), dl)


class RuleValidator(object):
    """
    This class is the primary facility for validating configs. It's always
    called in map_tool_to_destination and it's called for validating config
    directly through DynamicToolDestination.py
    """

    @classmethod
    def validate_rule(cls, rule_type, app, return_bool=False, *args, **kwargs):
        """
        This function is responsible for passing each rule to its relevant
        function.

        @type rule_type: str
        @param rule_type: the current rule's type

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on
                 return_bool)
        """
        if rule_type == 'file_size':
            return cls.__validate_file_size_rule(app, return_bool, *args, **kwargs)

        elif rule_type == 'num_input_datasets':
            return cls.__validate_num_input_datasets_rule(app, return_bool, *args, **kwargs)

        elif rule_type == 'records':
            return cls.__validate_records_rule(app, return_bool, *args, **kwargs)

        elif rule_type == 'arguments':
            return cls.__validate_arguments_rule(app, return_bool, *args, **kwargs)

    @classmethod
    def __validate_file_size_rule(
            cls, app, return_bool, original_rule, counter, tool):
        """
        This function is responsible for validating 'file_size' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on
                 return_bool)
        """

        rule = copy.deepcopy(original_rule)
        valid_rule = True

        # Users Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_users(
                valid_rule, return_bool, rule, tool, counter)

        # Nice_value Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_nice_value(
                valid_rule, return_bool, rule, tool, counter)

        # Destination Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_destination(
                valid_rule, app, return_bool, rule, tool, counter)

        # Bounds Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_bounds(
                valid_rule, return_bool, rule, tool, counter)

        if return_bool:
            return valid_rule

        else:
            return rule

    @classmethod
    def __validate_num_input_datasets_rule(
            cls, app, return_bool, original_rule, counter, tool):
        """
        This function is responsible for validating 'num_input_datasets' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on
                 return_bool)
        """

        rule = copy.deepcopy(original_rule)
        valid_rule = True

        # Users Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_users(
                valid_rule, return_bool, rule, tool, counter)

        # Nice_value Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_nice_value(
                valid_rule, return_bool, rule, tool, counter)

        # Destination Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_destination(
                valid_rule, app, return_bool, rule, tool, counter)

        # Bounds Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_bounds(
                valid_rule, return_bool, rule, tool, counter)

        if return_bool:
            return valid_rule

        else:
            return rule

    @classmethod
    def __validate_records_rule(cls, app, return_bool, original_rule, counter, tool):
        """
        This function is responsible for validating 'records' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on
                 return_bool)
        """

        rule = copy.deepcopy(original_rule)
        valid_rule = True

        # Users Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_users(
                valid_rule, return_bool, rule, tool, counter)

        # Nice_value Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_nice_value(
                valid_rule, return_bool, rule, tool, counter)

        # Destination Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_destination(
                valid_rule, app, return_bool, rule, tool, counter)

        # Bounds Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_bounds(
                valid_rule, return_bool, rule, tool, counter)

        if return_bool:
            return valid_rule

        else:
            return rule

    @classmethod
    def __validate_arguments_rule(
            cls, app, return_bool, original_rule, counter, tool):
        """
        This is responsible for validating 'arguments' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on
                return_bool)
        """

        rule = copy.deepcopy(original_rule)
        valid_rule = True

        # Users Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_users(
                valid_rule, return_bool, rule, tool, counter)

        # Nice_value Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_nice_value(
                valid_rule, return_bool, rule, tool, counter)

        # Destination Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_destination(
                valid_rule, app, return_bool, rule, tool, counter)

        # Arguments Verification (for rule_type arguments; read comment block at top
        # of function for clarification.
        if rule is not None:
            valid_rule, rule = cls.__validate_arguments(
                valid_rule, return_bool, rule, tool, counter)

        if return_bool:
            return valid_rule

        else:
            return rule

    @classmethod
    def __validate_nice_value(cls, valid_rule, return_bool, rule, tool, counter):
        """
        This function is responsible for validating nice_value.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it
                           encounters any abnormalities in the config.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type rule: dict
        @param rule: contains the original received rule

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @rtype: bool, dict (tuple)
        @return: validated rule and result of validation
        """

        if "nice_value" in rule:
            if rule["nice_value"] < -20 or rule["nice_value"] > 20:
                error = "nice_value goes from -20 to 20; rule " + str(counter)
                error += " in '" + str(tool) + "' has a nice_value of '"
                error += str(rule["nice_value"]) + "'."
                if not return_bool:
                    error += " Setting nice_value to 0."
                    rule["nice_value"] = 0

                if verbose:
                    log.debug(error)
                valid_rule = False

        else:
            error = "No nice_value found for rule " + str(counter) + " in '"
            error += str(tool) + "'."
            if not return_bool:
                error += " Setting nice_value to 0."
                rule["nice_value"] = 0
            if verbose:
                log.debug(error)
            valid_rule = False

        return valid_rule, rule

    @classmethod
    def __validate_destination(cls, valid_rule, app, return_bool, rule, tool, counter):
        """
        This function is responsible for validating destination.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it
                           encounters any abnormalities in the config.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type rule: dict
        @param rule: contains the original received rule

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @rtype: bool, dict (tuple)
        @return: validated rule and result of validation
        """

        if "fail_message" in rule:
            if "destination" not in rule or rule['destination'] != "fail":
                error = "Found a fail_message for rule " + str(counter)
                error += " in '" + str(tool) + "', but destination is not 'fail'!"
                if not return_bool:
                    error += " Setting destination to 'fail'."
                if verbose:
                    log.debug(error)

                valid_rule = False

            rule["destination"] = "fail"

        if "destination" in rule:
            suggestion = None
            if isinstance(rule["destination"], str):
                if rule["destination"] == "fail" and "fail_message" not in rule:
                    error = "Missing a fail_message for rule " + str(counter)
                    error += " in '" + str(tool) + "'."
                    if not return_bool:
                        error += " Adding generic fail_message."
                        message = "Invalid parameters for rule " + str(counter)
                        message += " in '" + str(tool) + "'."
                        rule["fail_message"] = message
                    if verbose:
                        log.debug(error)
                    valid_rule = False
                else:
                    is_valid = validate_destination(app, rule["destination"],
                               dest_err_tool_rule_dest, (tool, counter, rule["destination"]),
                               return_bool)
                    if not is_valid:
                        valid_rule = False
            elif isinstance(rule["destination"], dict):
                if ("priority" in rule["destination"]
                        and isinstance(rule["destination"]["priority"], dict)):

                    for priority in rule["destination"]["priority"]:
                        if priority not in priority_list:
                            error = "Invalid priority '"
                            error += str(priority) + "' for rule "
                            error += str(counter) + " in '" + str(tool) + "'."
                            suggestion = get_typo_correction(priority,
                                         priority_list, max_edit_dist)
                            if suggestion:
                                error += " Did you mean '" + str(suggestion) + "'?"
                            if not return_bool:
                                error += " Ignoring..."
                            if verbose:
                                log.debug(error)
                            valid_rule = False

                        elif not isinstance(rule["destination"]["priority"][priority], str):
                            error = "Cannot parse tool destination '"
                            error += str(rule["destination"]["priority"][priority])
                            error += "' for rule " + str(counter)
                            error += " in '" + str(tool) + "'."
                            if not return_bool:
                                error += " Ignoring..."
                            if verbose:
                                log.debug(error)
                            valid_rule = False
                        else:
                            is_valid = validate_destination(app,
                                rule["destination"]["priority"][priority],
                                dest_err_tool_rule_dest,
                                (tool, counter, rule["destination"]["priority"][priority]),
                                return_bool)
                            if not is_valid:
                                valid_rule = False
                else:
                    error = "No destination specified for rule " + str(counter)
                    error += " in '" + str(tool) + "'."
                    if not return_bool:
                        error += " Ignoring..."
                    if verbose:
                        log.debug(error)
                    valid_rule = False
            else:
                error = "No destination specified for rule " + str(counter)
                error += " in '" + str(tool) + "'."
                if not return_bool:
                    error += " Ignoring..."
                if verbose:
                    log.debug(error)
                valid_rule = False
        else:
            error = "No destination specified for rule " + str(counter)
            error += " in '" + str(tool) + "'."
            if not return_bool:
                error += " Ignoring..."
            if verbose:
                log.debug(error)
            valid_rule = False

        return valid_rule, rule

    @classmethod
    def __validate_bounds(cls, valid_rule, return_bool, rule, tool, counter):
        """
        This function is responsible for validating bounds.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it
                           encounters any abnormalities in the config.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type rule: dict
        @param rule: contains the original received rule

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @rtype: bool/None, dict (tuple)
        @return: validated rule (or None if invalid) and result of validation
        """

        if "upper_bound" in rule and "lower_bound" in rule:
            if rule["rule_type"] in ("file_size", "records"):
                upper_bound = str_to_bytes(rule["upper_bound"])
                lower_bound = str_to_bytes(rule["lower_bound"])
            else:
                upper_bound = rule["upper_bound"]
                lower_bound = rule["lower_bound"]

            if lower_bound == "Infinity":
                error = "Error: lower_bound is set to Infinity, but must be "
                error += "lower than upper_bound!"
                if not return_bool:
                    error += " Setting lower_bound to 0!"
                    lower_bound = 0
                    rule["lower_bound"] = 0
                else:
                    lower_bound = float('inf')
                if verbose:
                    log.debug(error)
                valid_rule = False

            if upper_bound == "Infinity":
                upper_bound = -1

            if upper_bound != -1 and lower_bound > upper_bound:

                error = "lower_bound exceeds upper_bound for rule " + str(counter)
                error += " in '" + str(tool) + "'."
                if not return_bool:
                    error += " Reversing bounds."
                    temp_upper_bound = rule["upper_bound"]
                    temp_lower_bound = rule["lower_bound"]
                    rule["upper_bound"] = temp_lower_bound
                    rule["lower_bound"] = temp_upper_bound
                if verbose:
                    log.debug(error)
                valid_rule = False

        else:
            error = "Missing bounds for rule " + str(counter)
            error += " in '" + str(tool) + "'."
            if not return_bool:
                error += " Ignoring rule."
                rule = None
            if verbose:
                log.debug(error)
            valid_rule = False

        return valid_rule, rule

    @classmethod
    def __validate_arguments(cls, valid_rule, return_bool, rule, tool, counter):
        """
        This function is responsible for validating arguments.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it
                           encounters any abnormalities in the config.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type rule: dict
        @param rule: contains the original received rule

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @rtype: bool/None, dict (tuple)
        @return: validated rule (or None if invalid) and result of validation
        """

        if "arguments" not in rule or not isinstance(rule["arguments"], dict):
            error = "No arguments found for rule " + str(counter) + " in '"
            error += str(tool) + "' despite being of type arguments."
            if not return_bool:
                error += " Ignoring rule."
                rule = None
            if verbose:
                log.debug(error)
            valid_rule = False

        return valid_rule, rule

    @classmethod
    def __validate_users(cls, valid_rule, return_bool, rule, tool, counter):
        """
        This function is responsible for validating users (if present).

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of
                            the validation, and not the validated rule itself.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it
                           encounters any abnormalities in the config.

        @type rule: dict
        @param rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is
                        currently being validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (tuple)
        @return: validated rule and result of validation
        """

        emailregex = r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$"

        if "users" in rule:
            if isinstance(rule["users"], list):
                for user in reversed(rule["users"]):
                    if not isinstance(user, str):
                        error = "Entry '" + str(user) + "' in users for rule "
                        error += str(counter) + " in tool '" + str(tool)
                        error += "' is in an " + "invalid format!"
                        if not return_bool:
                            error += " Ignoring entry."
                        if verbose:
                            log.debug(error)
                        valid_rule = False
                        rule["users"].remove(user)

                    else:
                        if re.match(emailregex, user) is None:
                            error = "Supplied email '" + str(user)
                            error += "' for rule " + str(counter) + " in tool '"
                            error += str(tool) + "' is in " + "an invalid format!"
                            if not return_bool:
                                error += " Ignoring email."
                            if verbose:
                                log.debug(error)
                            valid_rule = False
                            rule["users"].remove(user)

            else:
                error = "Couldn't find a list under 'users:'!"
                if not return_bool:
                    error += " Ignoring rule."
                    rule = None
                if verbose:
                    log.debug(error)
                valid_rule = False

            # post-processing checking to make sure we didn't just remove all the users
            # if we did, we should ignore the rule
            if rule is not None and rule["users"] is not None and len(rule["users"]) == 0:
                error = "No valid user emails were specified for rule " + str(counter)
                error += " in tool '" + str(tool) + "'!"
                if not return_bool:
                    error += " Ignoring rule."
                    rule = None
                if verbose:
                    log.debug(error)
                valid_rule = False

        return valid_rule, rule


def parse_yaml(path="/config/tool_destinations.yml",
               job_conf_path="/config/job_conf.xml", app=None, test=False,
               return_bool=False):
    """
    Get a yaml file from path and send it to validate_config for validation.

    @type path: str
    @param path: the path to the tool destinations config file

    @type job_conf_path: str
    @param job_conf_path: the path to the job config file

    @type test: bool
    @param test: indicates whether to run in test mode or production mode

    @type return_bool: bool
    @param return_bool: True when we are only interested in the result of the
                          validation, and not the validated rule itself.

    @rtype: bool, dict (depending on return_bool)
    @return: validated rule or result of validation (depending on return_bool)

    """

    if app is None:
        global destination_list
        destination_list = get_destination_list_from_job_config(job_conf_path)

    # Import file from path
    try:
        if test:
            config = load(path)
        else:
            if path == "/config/tool_destinations.yml":
                # os.path.realpath gets the path of DynamicToolDestination.py
                # and then os.path.join is used to go back four directories
                config_directory = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), '../../../..')

                opt_file = config_directory + path

            else:
                opt_file = path

            with open(opt_file, 'r') as stream:
                config = load(stream)

        # Test imported file
        try:
            if return_bool:
                valid_config = validate_config(config, app, return_bool)
            else:
                config = validate_config(config, app)
        except MalformedYMLException:
            if verbose:
                log.error(str(sys.exc_value))
            raise
    except ScannerError:
        if verbose:
            log.error("Config is too malformed to fix!")
        raise

    if return_bool:
        return valid_config

    else:
        return config


def validate_destination(app, destination, err_message, err_message_contents,
                         return_bool=True):
    """
    Validate received destination id.

    @type app:
    @param app: Current app

    @type destination: str
    @param destination: string containing the destination id that is being
                        validated

    @type err_message: str
    @param err_message: Error message to be formatted with the contents of
                        `err_message_contents` upon the event of invalid
                        destination

    @type err_message_contents: tuple
    @param err_message_contents: A tuple of strings to be placed in
                                 `err_message`

    @type return_bool: bool
    @param return_bool: Whether or not the calling function has been told to
                        return a boolean value or not. Determines whether or
                        not to print 'Ignoring...' after error messages.

    @rtype: bool
    @return: True if the destination is valid and False otherwise.
    """

    valid_destination = False
    suggestion = None

    if destination == 'fail' and err_message is dest_err_tool_rule_dest:  # It's a tool rule that is set to fail. It's valid
        valid_destination = True
    elif app is None:
        if destination in destination_list:
            valid_destination = True
        else:
            suggestion = get_typo_correction(destination,
                                             destination_list, max_edit_dist)
    elif app.job_config.get_destination(destination):
        valid_destination = True

    if not valid_destination:
        error = err_message % err_message_contents
        if suggestion:
            error += " Did you mean '" + suggestion + "'?"
        if not return_bool:
            error += " Ignoring..."
        if verbose:
            log.debug(error)

    return valid_destination


def validate_config(obj, app=None, return_bool=False,):
    """
    Validate received config.

    @type obj: dict
    @param obj: the entire contents of the config

    @type return_bool: bool
    @param return_bool: True when we are only interested in the result of the
                          validation, and not the validated rule itself.

    @rtype: bool, dict (depending on return_bool)
    @return: validated rule or result of validation (depending on return_bool)
    """

    global priority_list
    priority_list = set()

    def infinite_defaultdict():
        return collections.defaultdict(infinite_defaultdict)

    # Allow new_config to expand automatically when adding values to new levels
    new_config = infinite_defaultdict()

    global verbose
    verbose = False
    valid_config = True
    valid_rule = True
    tool_has_default = False

    if return_bool:
        verbose = True
    elif obj is not None and 'verbose' in obj and isinstance(obj['verbose'], bool):
        verbose = obj['verbose']
    else:
        valid_config = False
        if obj:
            log.debug("Verbose value '" + str(obj['verbose']) + "' is not True or False! Falling back to verbose...")
            verbose = True

    if not return_bool and verbose:
        log.debug("Running config validation...")
        # if this is false, then it's definitely because of verbose missing

    if not valid_config and return_bool:
        log.debug("Missing mandatory field 'verbose' in config!")

    # a list with the available rule_types. Can be expanded on easily in the future
    available_rule_types = ['file_size', 'num_input_datasets', 'records', 'arguments']

    if obj is not None:
        # in obj, there should always be only 5 categories: tools, default_destination,
        # default_priority, users, and verbose

        if 'default_destination' in obj:
            suggestion = None
            if isinstance(obj['default_destination'], str):
                is_valid = validate_destination(app, obj['default_destination'],
                                                dest_err_default_dest,
                                                (obj['default_destination']))
                if is_valid:
                    new_config["default_destination"] = obj['default_destination']
                else:
                    valid_config = False

            elif isinstance(obj['default_destination'], dict):

                if ('priority' in obj['default_destination'] and
                        isinstance(obj['default_destination']['priority'], dict)):

                    for priority in obj['default_destination']['priority']:
                        if isinstance(obj['default_destination']['priority'][priority],
                                      str):
                            priority_list.add(priority)
                            is_valid = validate_destination(
                                app, obj['default_destination']['priority'][priority],
                                dest_err_default_dest,
                                (obj['default_destination']['priority'][priority]))

                            if is_valid:
                                new_config["default_destination"]['priority'][priority] = (
                                    obj['default_destination']['priority'][priority])
                            else:
                                valid_config = False
                    if len(priority_list) < 1:
                        error = ("No valid priorities found!")
                        if verbose:
                            log.debug(error)
                        valid_config = False
                    else:
                        if 'default_priority' in obj:
                            if isinstance(obj['default_priority'], str):
                                if obj['default_priority'] in priority_list:
                                    new_config['default_priority'] = obj['default_priority']
                                else:
                                    error = ("Default priority '" + str(obj['default_priority'])
                                          + "' is not a valid priority.")
                                    suggestion = get_typo_correction(obj['default_priority'],
                                                 priority_list, max_edit_dist)
                                    if suggestion:
                                        error += " Did you mean '" + str(suggestion) + "'?"
                                    if verbose:
                                        log.debug(error)
                            else:
                                error = "default_priority in config is not valid."
                                if verbose:
                                    log.debug(error)
                                valid_config = False
                        else:
                            error = "No default_priority section found in config."
                            if 'med' in priority_list:
                                # set 'med' as fallback default priority, so
                                # old tool_destination.yml configs still work
                                error += " Setting 'med' as default priority."
                                new_config['default_priority'] = 'med'
                            else:
                                error += " Things may not run as expected!"
                                valid_config = False
                            if verbose:
                                log.debug(error)

                else:
                    error = "No global default destinations specified in config!"
                    if verbose:
                        log.debug(error)
                    valid_config = False
            else:
                error = "No global default destination specified in config!"
                if verbose:
                    log.debug(error)
                valid_config = False

        else:
            error = "No global default destination specified in config!"
            if verbose:
                log.debug(error)
            valid_config = False

        if 'users' in obj:
            if isinstance(obj['users'], dict):
                for user in obj['users']:
                    curr = obj['users'][user]

                    if isinstance(curr, dict):
                        if 'priority' in curr and isinstance(curr['priority'], str):

                            if curr['priority'] in priority_list:
                                new_config['users'][user]['priority'] = curr['priority']
                            else:
                                error = ("User '" + user + "', priority '"
                                      + str(curr['priority']) + "' is not defined "
                                      + "in the global default_destination section")
                                suggestion = get_typo_correction(curr['priority'],
                                             priority_list, max_edit_dist)
                                if suggestion:
                                    error += " Did you mean '" + str(suggestion) + "'?"
                                if verbose:
                                    log.debug(error)
                                valid_config = False
                        else:
                            error = "User '" + user + "' is missing a priority!"
                            if verbose:
                                log.debug(error)
                            valid_config = False
                    else:
                        error = "User '" + user + "' is missing a priority!"
                        if verbose:
                            log.debug(error)
                        valid_config = False
            else:
                error = "Users option is not a dictionary!"
                if verbose:
                    log.debug(error)
                valid_config = False

        if 'tools' in obj:
            for tool in obj['tools']:
                curr = obj['tools'][tool]

                # This check is to make sure we have a tool name, and not just
                # rules right way.
                if not isinstance(curr, list):
                    curr_tool_rules = []

                    if curr is not None:

                        # in each tool, there should always be only 2 sub-categories:
                        # default_destination (not mandatory) and rules (mandatory)
                        if "default_destination" in curr:
                            suggestion = None
                            if isinstance(curr['default_destination'], str):
                                is_valid = validate_destination(app,
                                    curr['default_destination'],
                                    dest_err_tool_default_dest,
                                    (tool, curr['default_destination']))
                                if is_valid:
                                    new_config['tools'][tool]['default_destination'] = (
                                        (curr['default_destination']))
                                    tool_has_default = True
                                else:
                                    valid_config = False
                            elif isinstance(curr['default_destination'], dict):

                                if ('priority' in curr['default_destination']
                                        and isinstance(curr['default_destination']['priority'], dict)):

                                    for priority in curr['default_destination']['priority']:
                                        destination = curr['default_destination']['priority'][priority]
                                        if priority in priority_list:
                                            if isinstance(destination, str):

                                                is_valid = validate_destination(
                                                    app, destination,
                                                    dest_err_tool_default_dest,
                                                    (tool, curr['default_destination']['priority'][priority]))
                                                if is_valid:
                                                    new_config['tools'][tool]['default_destination']['priority'][priority] = destination
                                                    tool_has_default = True
                                                else:
                                                    valid_config = False

                                            else:
                                                error = ("No default '" + str(priority)
                                                         + "' priority destination  for tool "
                                                         + str(tool) + " in config!")
                                                if verbose:
                                                    log.debug(error)
                                                valid_config = False

                                        else:
                                            error = ("Invalid default destination priority '"
                                                     + str(priority) + "' for '" + str(tool)
                                                     + "'.")
                                            suggestion = get_typo_correction(priority,
                                                         priority_list, max_edit_dist)
                                            if suggestion:
                                                error += " Did you mean '" + str(suggestion) + "'?"
                                            if verbose:
                                                log.debug(error)
                                            valid_config = False
                                else:
                                    error = "No default priority destinations specified"
                                    error += " for " + str(tool) + " in config!"
                                    if verbose:
                                        log.debug(error)
                                    valid_config = False

                        if "rules" in curr and isinstance(curr['rules'], list):
                            # under rules, there should only be a list of rules
                            curr_tool = curr
                            counter = 0

                            for rule in curr_tool['rules']:
                                if "rule_type" in rule:
                                    if rule['rule_type'] in available_rule_types:
                                        validated_rule = None
                                        counter += 1

                                        # if we're only interested in the result of
                                        # the validation, then only retrieve the
                                        # result
                                        if return_bool:
                                            valid_rule = RuleValidator.validate_rule(
                                                rule['rule_type'], app, return_bool,
                                                rule, counter, tool)

                                        # otherwise, retrieve the processed rule
                                        else:
                                            validated_rule = (
                                                RuleValidator.validate_rule(
                                                    rule['rule_type'],
                                                    app, return_bool,
                                                    rule, counter, tool))

                                        # if the result we get is False, then
                                        # indicate that the whole config is invalid
                                        if not valid_rule:
                                            valid_config = False

                                        # if we got a rule back that seems to be
                                        # valid (or was fixable) then append it to
                                        # list of ready-to-use tools
                                        if (not return_bool and
                                                validated_rule is not None):
                                            curr_tool_rules.append(
                                                copy.deepcopy(validated_rule))

                                    # if rule['rule_type'] in available_rule_types
                                    else:
                                        error = "Unrecognized rule_type '"
                                        error += rule['rule_type'] + "' "
                                        error += "found in '" + str(tool) + "'. "
                                        if not return_bool:
                                            error += "Ignoring..."
                                        if verbose:
                                            log.debug(error)
                                        valid_config = False

                                # if "rule_type" in rule
                                else:
                                    counter += 1
                                    error = "No rule_type found for rule "
                                    error += str(counter)
                                    error += " in '" + str(tool) + "'."
                                    if verbose:
                                        log.debug(error)
                                    valid_config = False

                        # if "rules" in curr and isinstance(curr['rules'], list):
                        elif not tool_has_default:
                            valid_config = False
                            error = "Tool '" + str(tool) + "' does not have"
                            error += " rules nor a default_destination!"
                            if verbose:
                                log.debug(error)

                    # if obj['tools'][tool] is not None:
                    else:
                        valid_config = False
                        error = "Config section for tool '" + str(tool) + "' is blank!"
                        if verbose:
                            log.debug(error)

                    if curr_tool_rules:
                        new_config['tools'][str(tool)]['rules'] = curr_tool_rules

                # if not isinstance(curr, list)
                else:
                    error = "Malformed YML; expected job name, "
                    error += "but found a list instead!"
                    if verbose:
                        log.debug(error)
                    valid_config = False

        # quickly run through categories to detect unrecognized types
        for category in obj.keys():
            if category not in valid_categories:
                error = "Unrecognized category '" + category
                error += "' found in config file!"
                if verbose:
                    log.debug(error)
                valid_config = False

    # if obj is not None
    else:
        if verbose:
            log.debug("No (or empty) config file supplied!")
        valid_config = False

    if not return_bool:
        if verbose:
            log.debug("Finished config validation.")

    if return_bool:
        return valid_config

    else:
        return new_config


def bytes_to_str(size, unit="YB"):
    '''
    Uses the bi convention: 1024 B = 1 KB since this method primarily
    has inputs of bytes for RAM

    @type size: int
    @param size: the size in int (bytes) to be converted to str

    @rtype: str
    @return return_str: the resulting string
    '''
    # converts size in bytes to most readable unit
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = 0

    # mostly called in order to convert "infinity"
    try:
        size_changer = int(size)
    except ValueError:
        error = "bytes_to_str passed uncastable non numeric value "
        raise ValueError(error + str(size))

    try:
        upto = units.index(unit.strip().upper())
    except ValueError:
        upto = 9

    while size_changer >= 1024 and i < upto:
        size_changer = size_changer / 1024.0
        i += 1

    if size_changer == -1:
        size_changer = "Infinity"
        i = 0

    try:
        return_str = "%.2f %s" % (size_changer, units[i])
    except TypeError:
        return_str = "%s" % (size_changer)

    return return_str


def str_to_bytes(size):
    '''
    Uses the bi convention: 1024 B = 1 KB since this method primarily
    has inputs of bytes for RAM

    @type size: str
    @param size: the size in str to be converted to int (bytes)

    @rtype: int
    @return curr_size: the resulting size converted from str
    '''
    units = ["", "b", "kb", "mb", "gb", "tb", "pb", "eb", "zb", "yb"]
    curr_size = size

    try:
        if size.lower() != "infinity":
            # Get the number
            try:
                curr_item = size.strip().split(" ")
                curr_size = "".join(curr_item)

                curr_size = int(curr_size)
            except ValueError:
                curr_item = size.strip().split(" ")
                curr_unit = curr_item[-1].strip().lower()
                curr_item = curr_item[0:-1]
                curr_size = "".join(curr_item)

                try:
                    curr_size = float(curr_size)
                except ValueError:
                    error = "Unable to convert size " + str(size)
                    raise MalformedYMLException(error)

            # Get the unit and convert to bytes
            try:
                pos = units.index(curr_unit)
                for x in range(pos, 1, -1):
                    curr_size *= 1024
            except ValueError:
                error = "Unable to convert size " + str(size)
                raise MalformedYMLException(error)
            except (UnboundLocalError, NameError):
                pass
        else:
            curr_size = -1
    except AttributeError:
        # If size is not a string (doesn't have .lower())
        pass

    return curr_size


def importer(test):
    """
    Uses Mock galaxy for testing or real galaxy for production

    @type test: bool
    @param test: True when being run from a test
    """
    global JobDestination
    global JobMappingException
    if test:
        class JobDestination(object):
            def __init__(self, *kwd):
                self.id = kwd.get('id')
                self.nativeSpec = kwd.get('params')['nativeSpecification']
                self.runner = kwd.get('runner')
        from galaxy.jobs.mapper import JobMappingException
    else:
        from galaxy.jobs import JobDestination
        from galaxy.jobs.mapper import JobMappingException


def map_tool_to_destination(
        job, app, tool, user_email, test=False, path=None, job_conf_path=None):
    """
    Dynamically allocate resources

    @param job: galaxy job
    @param app: current app
    @param tool: current tool

    @type test: bool
    @param test: True when running in test mode

    @type path: str
    @param path: path to tool_destinations.yml

    @type job_conf_path: str
    @param job_conf_path: path to job_conf.xml
    """
    importer(test)

    # set verbose to True by default, just in case (some tests fail without
    # this due to how the tests apparently work)
    global verbose
    verbose = True
    filesize_rule_present = False
    num_input_datasets_rule_present = False
    records_rule_present = False

    # Get configuration from tool_destinations.yml and job_conf.xml
    if path is None:
        path = app.config.tool_destinations_config_file
    if job_conf_path is None:
        job_conf_path = app.config.job_config_file

    try:
        config = parse_yaml(path, job_conf_path, app)
    except MalformedYMLException as e:
        raise JobMappingException(e)

    # Get all inputs from tool and databases
    inp_data = dict([(da.name, da.dataset) for da in job.input_datasets])
    inp_data.update([(da.name, da.dataset) for da in job.input_library_datasets])

    if config is not None and str(tool.old_id) in config['tools']:
        if 'rules' in config['tools'][str(tool.old_id)]:
            for rule in config['tools'][str(tool.old_id)]['rules']:
                if rule["rule_type"] == "file_size":
                    filesize_rule_present = True

                if rule["rule_type"] == "num_input_datasets":
                    num_input_datasets_rule_present = True

                if rule["rule_type"] == "records":
                    records_rule_present = True

    file_size = 0
    records = 0
    num_input_datasets = 0

    if filesize_rule_present or records_rule_present or num_input_datasets_rule_present:
        # Loop through the database and look for amount of records
        try:
            for line in inp_db:
                if line[0] == ">":
                    records += 1
        except NameError:
            pass
        # Loops through each input file and adds the size to the total
        # or looks through db for records
        for da in inp_data:
            try:
                # If the input is a file, check and add the size
                if inp_data[da] is not None and os.path.isfile(inp_data[da].file_name):
                    num_input_datasets += 1
                    if verbose:
                        message = "Loading file: " + str(da)
                        message += str(inp_data[da].file_name)
                        log.debug(message)

                    # Add to records if the file type is fasta
                    if inp_data[da].ext == "fasta":
                        if records_rule_present:
                            inp_db = open(inp_data[da].file_name)

                            # Try to find automatically computed sequences
                            metadata = inp_data[da].get_metadata()

                            try:
                                records += int(metadata.get("sequences"))
                            except (TypeError, KeyError):
                                for line in inp_db:
                                    if line[0] == ">":
                                        records += 1
                    if filesize_rule_present:
                        query_file = str(inp_data[da].file_name)
                        file_size += os.path.getsize(query_file)
            except AttributeError:
                # Otherwise, say that input isn't a file
                if verbose:
                    log.debug("Not a file: " + str(inp_data[da]))

        if verbose:
            if filesize_rule_present:
                log.debug("Total size: " + bytes_to_str(file_size))
            if records_rule_present:
                log.debug("Total amount of records: " + str(records))
            if num_input_datasets_rule_present:
                log.debug("Total number of files: " + str(num_input_datasets))

    matched_rule = None
    user_authorized = None
    rule_counter = 0

    # For each different rule for the tool that's running
    fail_message = None

    if fail_message is not None:
        destination = "fail"
    elif config is not None:

        # Get the default priority from the config if necessary.
        # If there isn't one, choose an arbitrary one as a fallback
        if "default_destination" in config:
            if isinstance(config['default_destination'], dict):
                if 'default_priority' in config:
                    default_priority = config['default_priority']
                    priority = default_priority

                else:
                    if len(priority_list) > 0:
                        default_priority = next(iter(priority_list))
                        priority = default_priority
                        error = ("No default priority found, arbitrarily setting '"
                                 + default_priority + "' as the default priority."
                                 + " Things may not work as expected!")
                        if verbose:
                            log.debug(error)

        # fetch priority information from workflow/job parameters
        job_parameter_list = job.get_parameters()
        workflow_params = None
        job_params = None
        if job_parameter_list is not None:
            for param in job_parameter_list:
                if param.name == "__workflow_resource_params__":
                    workflow_params = param.value
                if param.name == "__job_resource":
                    job_params = param.value

        # Priority coming from workflow invocation takes precedence over job specific priorities
        if workflow_params is not None:
            resource_params = json.loads(workflow_params)
            if 'priority' in resource_params:
                # For by_group mapping, this priority has already been validated when the
                # request was created.
                if resource_params['priority'] is not None:
                    priority = resource_params['priority']

        elif job_params is not None:
            resource_params = json.loads(job_params)
            if 'priority' in resource_params:
                if resource_params['priority'] is not None:
                    priority = resource_params['priority']

        # get the user's priority
        if "users" in config:
            if user_email in config["users"]:
                priority = config["users"][user_email]["priority"]

        if "default_destination" in config:
            if isinstance(config['default_destination'], str):
                destination = config['default_destination']
            else:
                if priority in config['default_destination']['priority']:
                    destination = config['default_destination']['priority'][priority]
                elif default_priority in config['default_destination']['priority']:
                    destination = (config['default_destination']['priority'][default_priority])
            config = config['tools']
            if str(tool.old_id) in config:
                if 'rules' in config[str(tool.old_id)]:
                    for rule in config[str(tool.old_id)]['rules']:
                        rule_counter += 1
                        user_authorized = False
                        if 'users' in rule and isinstance(rule['users'], list):
                            if user_email in rule['users']:
                                user_authorized = True
                        else:
                            user_authorized = True

                        if user_authorized:
                            matched = False
                            if rule["rule_type"] == "file_size":

                                # bounds comparisons
                                upper_bound = str_to_bytes(rule["upper_bound"])
                                lower_bound = str_to_bytes(rule["lower_bound"])

                                if upper_bound == -1:
                                    if lower_bound <= file_size:
                                        matched = True

                                else:
                                    if (lower_bound <= file_size and file_size < upper_bound):
                                        matched = True

                            elif rule["rule_type"] == "num_input_datasets":

                                # bounds comparisons
                                upper_bound = rule["upper_bound"]
                                lower_bound = rule["lower_bound"]

                                if upper_bound == "Infinity":
                                    if lower_bound <= num_input_datasets:
                                        matched = True
                                else:
                                    if (lower_bound <= num_input_datasets and num_input_datasets < upper_bound):
                                        matched = True

                            elif rule["rule_type"] == "records":

                                # bounds comparisons
                                upper_bound = str_to_bytes(rule["upper_bound"])
                                lower_bound = str_to_bytes(rule["lower_bound"])

                                if upper_bound == -1:
                                    if lower_bound <= records:
                                        matched = True

                                else:
                                    if lower_bound <= records and records < upper_bound:
                                        matched = True

                            elif rule["rule_type"] == "arguments":
                                options = job.get_param_values(app)
                                matched = True
                                # check if the args in the config file are available
                                for arg in rule["arguments"]:
                                    arg_dict = {arg: rule["arguments"][arg]}
                                    arg_keys_list = []
                                    get_keys_from_dict(arg_dict, arg_keys_list)
                                    try:
                                        options_value = reduce(dict.__getitem__, arg_keys_list, options)
                                        arg_value = reduce(dict.__getitem__, arg_keys_list, arg_dict)
                                        if (arg_value != options_value):
                                            matched = False
                                    except KeyError:
                                        matched = False
                                        if verbose:
                                            error = "Argument '" + str(arg)
                                            error += "' not recognized!"
                                            log.debug(error)

                            # if we matched a rule
                            if matched:
                                if (matched_rule is None or rule["nice_value"]
                                        < matched_rule["nice_value"]):
                                    matched_rule = rule
                        # if user_authorized
                        else:
                            if verbose:
                                error = "User email '" + str(user_email) + "' not "
                                error += "specified in list of authorized users for "
                                error += "rule " + str(rule_counter) + " in tool '"
                                error += str(tool.old_id) + "'! Ignoring rule."
                                log.debug(error)

            # if str(tool.old_id) in config
            else:
                error = "Tool '" + str(tool.old_id) + "' not specified in config. "
                error += "Using default destination."
                if verbose:
                    log.debug(error)

            if matched_rule is None:
                if "default_destination" in config[str(tool.old_id)]:
                    default_tool_destination = (config[str(tool.old_id)]['default_destination'])
                    if isinstance(default_tool_destination, str):
                        destination = default_tool_destination
                    else:
                        if priority in default_tool_destination['priority']:
                            destination = default_tool_destination['priority'][priority]
                        elif default_priority in default_tool_destination['priority']:
                            destination = (default_tool_destination['priority'][default_priority])
                        # else global default destination is used
            else:
                if isinstance(matched_rule["destination"], str):
                    destination = matched_rule["destination"]
                else:
                    if priority in matched_rule["destination"]["priority"]:
                        destination = matched_rule["destination"]["priority"][priority]
                    elif default_priority in matched_rule["destination"]["priority"]:
                        destination = (matched_rule["destination"]["priority"][default_priority])
                    # else global default destination is used

        # if "default_destination" in config
        else:
            destination = "fail"
            fail_message = "Job '" + str(tool.old_id) + "' failed; "
            fail_message += "no global default destination specified in config!"

    # if fail_message is not None
    # elif config is not None
    else:
        destination = "fail"
        fail_message = "No config file supplied!"

    if destination == "fail":
        if fail_message:
            raise JobMappingException(fail_message)
        else:
            raise JobMappingException(matched_rule["fail_message"])

    if config is not None:
        if destination == "fail":
            output = "An error occurred: " + fail_message
            log.debug(output)
        else:
            output = "Running '" + str(tool.old_id) + "' with '"
            output += destination + "'."
            log.debug(output)

    return destination


def get_destination_list_from_job_config(job_config_location):
    """
    returns A list of all destination IDs declared in the job configuration

    @type job_config_location: str
    @param job_config_location: The location of the job config file relative
                to the galaxy root directory. If NoneType, defaults to
                galaxy/config/job_conf.xml,
                galaxy/config/job_conf.xml.sample_advanced, or
                galaxy/config/job_conf.xml.sample_basic
                (first one that exists)

    @rtype: list
    @return: A list of all of the destination IDs declared in the job
                configuration file.
    """
    global destination_list

    # os.path.realpath gets the path of DynamicToolDestination.py
    # and then os.path.join is used to go back four directories

    config_location = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../../..')

    if job_config_location:
        local_path = re.compile('^/config/.+$')
        if local_path.match(job_config_location):
            job_config_location = config_location + job_config_location
    else:  # Pick one of the default ones
        message = "* No job config specified, "
        if os.path.isfile(config_location + "/config/job_conf.xml"):
            job_config_location = config_location + "/config/job_conf.xml"
            message += "using 'config/job_conf.xml'. *"

        elif os.path.isfile(config_location +
                "/config/job_conf.xml.sample_advanced"):
            job_config_location = (config_location
                + "/config/job_conf.xml.sample_advanced")
            message += "using 'config/job_conf.xml.sample_advanced'. *"

        elif os.path.isfile(config_location +
                "/config/job_conf.xml.sample_basic"):
            job_config_location = (config_location
                + "/config/job_conf.xml.sample_basic")
            message += "using 'config/job_conf.xml.sample_basic'. *"
        else:
            message += ("and no default job configs in 'config/'. "
                    + "Expect lots of failures. *")

        if verbose:
            log.debug(message)

    if job_config_location:
        job_conf = ET.parse(job_config_location)

        # Add all destination IDs from the job configuration xml file
        for destination in job_conf.getroot().iter("destination"):
            if isinstance(destination.get("id"), str):
                destination_list.add(destination.get("id"))

            else:
                error = "Destination ID '" + str(destination)
                error += "' in job configuration file cannot be"
                error += " parsed. Things may not work as expected!"
                log.debug(error)

    return destination_list


def get_edit_distance(source, target):
    """
    returns the edit distance (levenshtein distance) between two strings.
    code from:
    en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance

    @type str1: str
    @param str1: The first string

    @type str2: str
    @param str2: The second string

    @rtype: int
    @return: The edit distance between str1 and str2
    """

    if len(source) < len(target):
        return get_edit_distance(target, source)

    # So now we have len(source) >= len(target).
    if len(target) == 0:
        return len(source)

    # We call tuple() to force strings to be used as sequences
    # ('c', 'a', 't', 's') - numpy uses them as values by default.
    source = np.array(tuple(source))
    target = np.array(tuple(target))

    # We use a dynamic programming algorithm, but with the
    # added optimization that we only need the last two rows
    # of the matrix.
    previous_row = np.arange(target.size + 1)
    for s in source:
        # Insertion (target grows longer than source):
        current_row = previous_row + 1

        # Substitution or matching:
        # Target and source items are aligned, and either
        # are different (cost of 1), or are the same (cost of 0).
        current_row[1:] = np.minimum(
            current_row[1:],
            np.add(previous_row[:-1], target != s))

        # Deletion (target grows shorter than source):
        current_row[1:] = np.minimum(
            current_row[1:],
            current_row[0:-1] + 1)

        previous_row = current_row

    return previous_row[-1]


def get_typo_correction(typo_str, word_set, max_dist):
    """
    returns the string in a set that closest matches the
    input string, as long as the edit distance between them
    is equal to or smaller than a value, or the words are
    the same when case is not considered. If there are no
    appropriate matches, nothing is returned instead.

    @type typo_str: str
    @param typo_str: The string to be compared

    @type word_set: set of str
    @param word_set: The set of strings to compare to

    @type max_dist: int
    @param max_dist: the largest allowed edit distance between
                    the word and the result. If nothing is
                    within this range, nothing is returned

    @rtype: str or NoneType
    @return: The closest matching string, or None, if no strings
    being compared to are within max_dist edit distance.
    """

    # Start curr_best out as the largest
    # edit distance we will tolerate plus one
    curr_best = max_dist + 1
    suggestion = None

    for valid_word in word_set:
        # If we've already found a best match,
        # don't bother checking anything else.
        if curr_best > 0:
            if typo_str.lower() == valid_word.lower():
                # if something matches when case insensitive,
                # it is automatically set as the best
                suggestion = valid_word
                curr_best = 0
            else:
                edit_distance = get_edit_distance(typo_str, valid_word)
                if edit_distance < curr_best:
                    suggestion = valid_word
                    curr_best = edit_distance

    return suggestion


if __name__ == '__main__':
    """
    This function is responsible for running the app if directly run through
    the commandline. It offers the ability to specify a config through the
    commandline for checking whether or not it is a valid config. It's to be
    run from within Galaxy, assuming it is installed correctly within the
    proper directories in Galaxy, and it looks for the config file in
    galaxy/config/. It can also be run with a path pointing to a config file if
    not being run directly from inside Galaxy install directory.
    """
    verbose = True

    parser = argparse.ArgumentParser()
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    parser.add_argument(
        '-c', '--check-config', dest='check_config', nargs='?',
        help='Use this option to validate tool_destinations.yml.'
             + ' Optionally, provide the path to the tool_destinations.yml'
             + ' that you would like to check, and/or the path to the related'
             + ' job_conf.xml. Default: galaxy/config/tool_destinations.yml'
             + 'and galaxy/config/job_conf.xml')

    parser.add_argument(
        '-j', '--job-config', dest='job_config')

    parser.add_argument(
        '-V', '--version', action='version', version="%(prog)s " + __version__)

    args = parser.parse_args()

    # if run with no arguments, display the help message
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    job_config_location = args.job_config

    if args.check_config:
        valid_config = parse_yaml(path=args.check_config,
                                  job_conf_path=job_config_location,
                                  return_bool=True)
    else:
        valid_config = parse_yaml(path="/config/tool_destinations.yml",
                                  job_conf_path=job_config_location,
                                  return_bool=True)

    if valid_config:
        print("Configuration is valid!")
    else:
        print("Errors detected; config not valid!")
