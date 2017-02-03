from __future__ import print_function

__version__ = '1.0.0'

from yaml import load

import argparse
import logging
import os
import sys
import copy
import collections
import re


# log to galaxy's logger
log = logging.getLogger(__name__)

# does a lot more logging when set to true
verbose = True


class MalformedYMLException(Exception):
    pass


class ScannerError(Exception):
    pass


class RuleValidator:
    """
    This class is the primary facility for validating configs. It's always called
    in map_tool_to_destination and it's called for validating config directly through
    DynamicToolDestination.py
    """

    @classmethod
    def validate_rule(cls, rule_type, return_bool=False, *args, **kwargs):
        """
        This function is responsible for passing each rule to its relevant function.

        @type rule_type: str
        @param rule_type: the current rule's type

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on return_bool)
        """
        if rule_type == 'file_size':
            return cls.__validate_file_size_rule(return_bool, *args, **kwargs)

        elif rule_type == 'num_input_datasets':
            return cls.__validate_num_input_datasets_rule(return_bool, *args, **kwargs)

        elif rule_type == 'records':
            return cls.__validate_records_rule(return_bool, *args, **kwargs)

        elif rule_type == 'arguments':
            return cls.__validate_arguments_rule(return_bool, *args, **kwargs)

    @classmethod
    def __validate_file_size_rule(
            cls, return_bool, original_rule, counter, tool):
        """
        This function is responsible for validating 'file_size' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on return_bool)
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
                valid_rule, return_bool, rule, tool, counter)

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
            cls, return_bool, original_rule, counter, tool):
        """
        This function is responsible for validating 'num_input_datasets' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on return_bool)
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
                valid_rule, return_bool, rule, tool, counter)

        # Bounds Verification #
        if rule is not None:
            valid_rule, rule = cls.__validate_bounds(
                valid_rule, return_bool, rule, tool, counter)

        if return_bool:
            return valid_rule

        else:
            return rule

    @classmethod
    def __validate_records_rule(cls, return_bool, original_rule, counter, tool):
        """
        This function is responsible for validating 'records' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on return_bool)
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
                valid_rule, return_bool, rule, tool, counter)

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
            cls, return_bool, original_rule, counter, tool):
        """
        This is responsible for validating 'arguments' rules.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (depending on return_bool)
        @return: validated rule or result of validation (depending on return_bool)
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
                valid_rule, return_bool, rule, tool, counter)

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

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it encounters any
                       abnormalities in the config.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

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
            error = "No nice_value found for rule " + str(counter) + " in '" + str(tool)
            error += "'."
            if not return_bool:
                error += " Setting nice_value to 0."
                rule["nice_value"] = 0
            if verbose:
                log.debug(error)
            valid_rule = False

        return valid_rule, rule

    @classmethod
    def __validate_destination(cls, valid_rule, return_bool, rule, tool, counter):
        """
        This function is responsible for validating destination.

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it encounters any
                       abnormalities in the config.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

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
            elif isinstance(rule["destination"], dict):
                if ("priority" in rule["destination"] and isinstance(rule["destination"]["priority"], dict)):
                    if "med" not in rule["destination"]["priority"]:
                        error = "No 'med' priority destination for rule " + str(counter)
                        error += " in '" + str(tool) + "'."
                        if not return_bool:
                            error += " Ignoring..."
                        if verbose:
                            log.debug(error)
                        valid_rule = False
                    else:
                        for priority in rule["destination"]["priority"]:
                            if priority not in ["low", "med", "high"]:
                                error = "Invalid priority destination '" + str(priority)
                                error += "' for rule " + str(counter)
                                error += " in '" + str(tool) + "'."
                                if not return_bool:
                                    error += " Ignoring..."
                                if verbose:
                                    log.debug(error)
                                valid_rule = False
                            elif not isinstance(rule["destination"]["priority"][priority], str):
                                error = "No '" + str(priority)
                                error += "'priority destination for rule " + str(counter)
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

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it encounters any
                       abnormalities in the config.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool/None, dict (tuple)
        @return: validated rule (or None if invalid) and result of validation
        """

        if "upper_bound" in rule and "lower_bound" in rule:
            if rule["rule_type"] == "file_size":
                upper_bound = str_to_bytes(rule["upper_bound"])
                lower_bound = str_to_bytes(rule["lower_bound"])
            else:
                upper_bound = rule["upper_bound"]
                lower_bound = rule["lower_bound"]

            if lower_bound == "Infinity":
                error = "Error: lower_bound is set to Infinity, but must be lower than "
                error += "upper_bound!"
                if not return_bool:
                    error += " Setting lower_bound to 0!"
                    lower_bound = 0
                    rule["lower_bound"] = 0
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

        @type return_bool: bool
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it encounters any
                       abnormalities in the config.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

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
        @param return_bool: True when we are only interested in the result of the
                              validation, and not the validated rule itself.

        @type valid_rule: bool
        @param valid_rule: returns True if everything is valid. False if it encounters any
                       abnormalities in the config.

        @type original_rule: dict
        @param original_rule: contains the original received rule

        @type counter: int
        @param counter: this counter is used to identify what rule # is currently being
                        validated. Necessary for log output.

        @type tool: str
        @param tool: the name of the current tool. Necessary for log output.

        @rtype: bool, dict (tuple)
        @return: validated rule and result of validation
        """

        emailregex = "^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$"

        if "users" in rule:
            if isinstance(rule["users"], list):
                for user in reversed(rule["users"]):
                    if not isinstance(user, str):
                        error = "Entry '" + str(user) + "' in users for rule "
                        error += str(counter) + " in tool '" + str(tool) + "' is in an "
                        error += "invalid format!"
                        if not return_bool:
                            error += " Ignoring entry."
                        if verbose:
                            log.debug(error)
                        valid_rule = False
                        rule["users"].remove(user)

                    else:
                        if re.match(emailregex, user) is None:
                            error = "Supplied email '" + str(user) + "' for rule "
                            error += str(counter) + " in tool '" + str(tool) + "' is in "
                            error += "an invalid format!"
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


def parse_yaml(path="/config/tool_destinations.yml", test=False, return_bool=False):
    """
    Get a yaml file from path and send it to validate_config for validation.

    @type path: str
    @param path: the path to the config file

    @type test: bool
    @param test: indicates whether to run in test mode or production mode

    @type return_bool: bool
    @param return_bool: True when we are only interested in the result of the
                          validation, and not the validated rule itself.

    @rtype: bool, dict (depending on return_bool)
    @return: validated rule or result of validation (depending on return_bool)

    """
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
                valid_config = validate_config(config, return_bool)
            else:
                config = validate_config(config)
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


def validate_config(obj, return_bool=False):
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

    if not return_bool and verbose:
        log.debug("Running config validation...")
        # if this is false, then it's definitely because of verbose missing

    if not valid_config and return_bool:
        log.debug("Missing mandatory field 'verbose' in config!")

    # a list with the available rule_types. Can be expanded on easily in the future
    available_rule_types = ['file_size', 'num_input_datasets', 'records', 'arguments']

    if obj is not None:
        # in obj, there should always be only 4 categories: tools, default_destination,
        # users, and verbose

        if 'default_destination' in obj:
            if isinstance(obj['default_destination'], str):
                new_config["default_destination"] = obj['default_destination']
            elif isinstance(obj['default_destination'], dict):
                if ('priority' in obj['default_destination'] and
                        isinstance(obj['default_destination']['priority'], dict)):
                    if 'med' not in obj['default_destination']['priority']:
                        error = "No default 'med' priority destination!"
                        if verbose:
                            log.debug(error)
                        valid_config = False
                    else:
                        for priority in obj['default_destination']['priority']:
                            if priority in ['low', 'med', 'high']:
                                if isinstance(
                                        obj['default_destination']['priority'][priority],
                                        str):
                                    new_config['default_destination']['priority'][
                                        priority] = obj[
                                            'default_destination']['priority'][priority]
                                else:
                                    error = ("No default '" + str(priority) +
                                             "' priority destination in config!")
                                    if verbose:
                                        log.debug(error)
                                    valid_config = False
                            else:
                                error = ("Invalid default priority destination '" +
                                         str(priority) + "' found in config!")
                                if verbose:
                                    log.debug(error)
                                valid_config = False
                else:
                    error = "No default priority destinations specified in config!"
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
                            if curr['priority'] in ['low', 'med', 'high']:
                                new_config['users'][user]['priority'] = curr['priority']
                            else:
                                error = ("User '" + user + "', priority is not valid!" +
                                         " Must be either low, med, or high.")
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
                            if isinstance(curr['default_destination'], str):
                                new_config['tools'][tool]['default_destination'] = (curr['default_destination'])
                                tool_has_default = True
                            elif isinstance(curr['default_destination'], dict):
                                if ('priority' in curr['default_destination'] and isinstance(curr['default_destination']['priority'], dict)):
                                    if ('med' not in curr['default_destination']['priority']):
                                        error = "No default 'med' priority destination "
                                        error += "for " + str(tool) + "!"
                                        if verbose:
                                            log.debug(error)
                                        valid_config = False
                                    else:
                                        for priority in curr['default_destination']['priority']:
                                            destination = curr['default_destination']['priority'][priority]
                                            if priority in ['low', 'med', 'high']:
                                                if isinstance(destination, str):
                                                    new_config['tools'][tool]['default_destination']['priority'][priority] = destination
                                                    tool_has_default = True
                                                else:
                                                    error = ("No default '" +
                                                             str(priority) +
                                                             "' priority destination " +
                                                             "for " + str(tool) +
                                                             " in config!")
                                                    if verbose:
                                                        log.debug(error)
                                                    valid_config = False
                                            else:
                                                error = ("Invalid default priority " +
                                                         "destination '" + str(priority) +
                                                         "' for " + str(tool) +
                                                         "found in config!")
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
                                                rule['rule_type'], return_bool,
                                                rule, counter, tool)

                                        # otherwise, retrieve the processed rule
                                        else:
                                            validated_rule = (
                                                RuleValidator.validate_rule(
                                                    rule['rule_type'],
                                                    return_bool,
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
                            error = "Tool '" + str(tool) + "' does not have rules nor a"
                            error += " default_destination!"
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
            if not (category == 'verbose' or category == 'tools' or
                    category == 'default_destination' or category == 'users'):
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
        class JobDestionation(object):
            def __init__(self, *kwd):
                self.id = kwd.get('id')
                self.nativeSpec = kwd.get('params')['nativeSpecification']
                self.runner = kwd.get('runner')
        from galaxy.jobs.mapper import JobMappingException
    else:
        from galaxy.jobs import JobDestination
        from galaxy.jobs.mapper import JobMappingException


def map_tool_to_destination(
        job, app, tool, user_email, test=False, path=None):
    """
    Dynamically allocate resources

    @param job: galaxy job
    @param app: current app
    @param tool: current tool

    @type test: bool
    @param test: True when running in test mode

    @type path: str
    @param path: path to tool_destinations.yml
    """
    importer(test)

    # set verbose to True by default, just in case (some tests fail without this due to
    # how the tests apparently work)
    global verbose
    verbose = True
    filesize_rule_present = False
    num_input_datasets_rule_present = False
    records_rule_present = False

    # Get configuration from tool_destinations.yml
    if path is None:
        path = app.config.tool_destinations_config_file

    try:
        config = parse_yaml(path)
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
        # Loop through each input file and adds the size to the total
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
                    elif filesize_rule_present:
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

    # set default priority to med
    default_priority = 'med'
    priority = default_priority

    if config is not None:
        # get the users priority
        if "users" in config:
            if user_email in config["users"]:
                priority = config["users"][user_email]["priority"]

        if "default_destination" in config:
            if isinstance(config['default_destination'], str):
                destination = config['default_destination']
            else:
                if priority in config['default_destination']['priority']:
                    destination = config['default_destination']['priority'][priority]
                else:
                    destination = ( config['default_destination']['priority'][default_priority])
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
                                    if arg in options:
                                        if rule["arguments"][arg] != options[arg]:
                                            matched = False
                                            options = "test"
                                    else:
                                        matched = False
                                        if verbose:
                                            error = "Argument '" + str(arg)
                                            error = + "' not recognized!"
                                            log.debug(error)

                            # if we matched a rule
                            if matched:
                                if (matched_rule is None or rule["nice_value"] < matched_rule["nice_value"]):
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
                        else:
                            destination = (default_tool_destination['priority'][default_priority])
            else:
                if isinstance(matched_rule["destination"], str):
                    destination = matched_rule["destination"]
                else:
                    if priority in matched_rule["destination"]["priority"]:
                        destination = matched_rule["destination"]["priority"][priority]
                    else:
                        destination = (matched_rule["destination"]["priority"][default_priority])

        # if "default_destination" in config
        else:
            destination = "fail"
            fail_message = "Job '" + str(tool.old_id) + "' failed; "
            fail_message += "no global default destination specified in config!"

    # if config is not None
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

        else:
            output = "Running '" + str(tool.old_id) + "' with '"
            output += destination + "'."
            log.debug(output)

    return destination


if __name__ == '__main__':
    """
    This function is responsible for running the app if directly run through the
    commandline. It offers the ability to specify a config through the commandline
    for checking whether or not it is a valid config. It's to be run from within Galaxy,
    assuming it is installed correctly within the proper directories in Galaxy, and it
    looks for the config file in galaxy/config/. It can also be run with a path pointing
    to a config file if not being run directly from inside Galaxy install directory.
    """
    verbose = True

    parser = argparse.ArgumentParser()
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    parser.add_argument(
        '-c', '--check-config', dest='check_config', nargs='?',
        help='Use this option to validate tool_destinations.yml.' +
        ' Optionally, provide the path to the tool_destinations.yml' +
        ' that you would like to check. Default: galaxy/config/tool_destinations.yml')

    parser.add_argument(
        '-V', '--version', action='version', version="%(prog)s " + __version__)

    args = parser.parse_args()

    # if run with no arguments, display the help message
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.check_config:
        valid_config = parse_yaml(path=args.check_config, return_bool=True)

    else:
        valid_config = parse_yaml(path="/config/tool_destinations.yml", return_bool=True)

    if valid_config:
        print("Configuration is valid!")
    else:
        print("Errors detected; config not valid!")
