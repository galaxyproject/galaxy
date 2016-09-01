# =============================================Valid XML===================================================
# One job, one rule
vYMLTest1 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: 0
            lower_bound: 0
            upper_bound: 100000000
            destination: things
    default_destination: waffles_default
    verbose: True
"""

vdictTest1_yml = {
    "tools": {
        "spades": {
            "rules": [
                {
                    "rule_type": "file_size",
                    "nice_value": 0,
                    "lower_bound": 0,
                    "upper_bound": 100000000,
                    "destination": "things"
                },
            ]
        }
    },
    'default_destination': "waffles_default"
}

# Multiple jobs, multiple rules
vYMLTest2 = '''
    tools:
      spades:
        default_destination: waffles_default
      smalt:
        rules:
          - rule_type: file_size
            nice_value: 0
            lower_bound: 0
            upper_bound: 100000000
            fail_message: Too few reads for smalt to work
            destination: fail
          - rule_type: file_size
            nice_value: 0
            lower_bound: 100000000
            upper_bound: Infinity
            fail_message: Too few reads for smalt to work
            destination: fail
    default_destination: waffles_low
    verbose: True
'''

vdictTest2_yml = {
    "tools": {
        "spades": {
            "default_destination": "waffles_default"
        },
        "smalt": {
            "rules": [
                {
                    "rule_type": "file_size",
                    'nice_value': 0,
                    "lower_bound": 0,
                    "upper_bound": 100000000,
                    "fail_message": "Too few reads for smalt to work",
                    "destination": "fail"
                }, {
                    "rule_type": "file_size",
                    'nice_value': 0,
                    "lower_bound": 100000000,
                    "upper_bound": "Infinity",
                    "fail_message": "Too few reads for smalt to work",
                    "destination": "fail"
                }
            ]
        }
    },
    'default_destination': "waffles_low"
}

# Rule with extra attribute
vYMLTest3 = '''
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: 0
            hax: 1337
            lower_bound: 0
            upper_bound: 100000000
            fail_message: Whats hax
            destination: fail
    default_destination: waffles_default
    verbose: True
'''

vdictTest3_yml = {
    "tools": {
        "spades": {
            "rules": [
                {
                    "rule_type": "file_size",
                    'nice_value': 0,
                    "hax": 1337,
                    "lower_bound": 0,
                    "upper_bound": 100000000,
                    "fail_message": "Whats hax",
                    "destination": "fail"
                }
            ]
        }
    },
    'default_destination': "waffles_default"
}

# Arguments type
vYMLTest4 = """
    tools:
      spades:
        rules:
          - rule_type: arguments
            nice_value: 0
            arguments:
              careful: true
            fail_message: Failure
            destination: fail
    default_destination: waffles_default
    verbose: True
"""

vdictTest4_yml = {
    "tools": {
        "spades": {
            "rules": [
                {
                    "rule_type": "arguments",
                    'nice_value': 0,
                    "arguments": {
                        "careful": True,
                    },
                    "fail_message": "Failure",
                    "destination": "fail"
                }
            ]
        }
    },
    'default_destination': "waffles_default"
}

# Records type
vYMLTest5 = '''
    tools:
      spades:
        rules:
          - rule_type: records
            nice_value: 0
            lower_bound: 0
            upper_bound: 100000000
            destination: waffles_low_4
    default_destination: waffles_default
    verbose: True
'''

vdictTest5_yml = {
    "tools": {
        "spades": {
            "rules": [
                {
                    "rule_type": "records",
                    'nice_value': 0,
                    "lower_bound": 0,
                    "upper_bound": 100000000,
                    "destination": "waffles_low_4"
                }
            ]
        }
    },
    'default_destination': "waffles_default"
}

# Num_input_datasets type
vYMLTest6 = '''
    tools:
      spades:
        default_destination: waffles_default
      smalt:
        rules:
          - rule_type: num_input_datasets
            nice_value: 0
            lower_bound: 0
            upper_bound: 200
            destination: cluster_low_4
          - rule_type: num_input_datasets
            nice_value: 0
            lower_bound: 200
            upper_bound: Infinity
            destination: cluster_high_32
    default_destination: waffles_low
    verbose: True
'''

vdictTest6_yml = {
    "tools": {
        "spades": {
            "default_destination": "waffles_default"
        },
        "smalt": {
            "rules": [
                {
                    "rule_type": "num_input_datasets",
                    'nice_value': 0,
                    "lower_bound": 0,
                    "upper_bound": 200,
                    "destination": "cluster_low_4"
                }, {
                    "rule_type": "num_input_datasets",
                    'nice_value': 0,
                    "lower_bound": 200,
                    "upper_bound": "Infinity",
                    "destination": "cluster_high_32"
                }
            ]
        }
    },
    'default_destination': "waffles_low"
}

# One job, one rule, and priority destinations
vYMLTest7 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: 0
            lower_bound: 0
            upper_bound: 100000000
            destination:
              priority:
                med: things
    default_destination:
      priority:
        med: waffles_default
    users:
      user@example.com:
        priority: med
    verbose: True
"""

vdictTest7_yml = {
    "tools": {
        "spades": {
            "rules": [
                {
                    "rule_type": "file_size",
                    "nice_value": 0,
                    "lower_bound": 0,
                    "upper_bound": 100000000,
                    "destination": {
                        'priority': {
                            'med': 'things'
                        }
                    }
                },
            ]
        }
    },
    'default_destination': {
        'priority': {
            'med': 'waffles_default'
        }
    },
    'users': {
        'user@example.com': {
            'priority': 'med'
        }
    }
}
# =====================================================Invalid XML tests==========================================================

# Empty file
ivYMLTest2 = ""

# Job without name
ivYMLTest3 = '''
    tools:
      rules:
        - rule_type: file_size
          nice_value: 0
          upper_bound: 100
          lower_bound: 0
          destination: fail
    default_destination: waffles_default
    verbose: True
'''

iv3dict = {
    'default_destination': "waffles_default"
}

# Rule missing type
ivYMLTest4 = '''
    tools:
      spades:
        rules:
          - nice_value: 0
            lower_bound: 0
            upper_bound: 0
            fail_message: No type...
            destination: fail
    default_destination: waffles_default
    verbose: True
'''

# Rule missing attribute
ivYMLTest51 = '''
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: 0
            upper_bound: 0
            fail_message: No type...
            destination: fail
    default_destination: waffles_default
    verbose: True
'''

# Rule missing attribute
ivYMLTest52 = '''
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: 0
            lower_bound: 0
            fail_message: No type...
            destination: fail
    default_destination: waffles_default
    verbose: True
'''

# Rule missing attribute
ivYMLTest53 = '''
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: 0
            lower_bound: 0
            upper_bound: 0
            fail_message: No type...
    default_destination: waffles_default
    verbose: True
'''

ivDict53 = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'upper_bound': 0,
                    'rule_type':
                    'file_size',
                    'fail_message':
                    'No type...',
                    'nice_value': 0,
                    'lower_bound': 0,
                    'destination': 'fail'
                }
            ]
        }
    }
}

# Rule unknown type
ivYMLTest6 = '''
    tools:
      spades:
        rules:
          - rule_type: iencs
            nice_value: 0
            lower_bound: 0
            upper_bound: 0
            fail_message: No type...
            destination: fail
    default_destination: waffles_default
    verbose: True
'''

# No default destination
ivYMLTest7 = '''
    default_destination:
    verbose: True
'''

ivDict = {
    'default_destination': "waffles_default"
}

# Invalid category
ivYMLTest8 = '''
    ice_cream:
    verbose: True
'''

# Tool rule fail no fail_message and apparently no nice_value
ivYMLTest91 = '''
    tools:
      spades:
        rules:
          - rule_type: file_size
            lower_bound: 0
            upper_bound: 0
            destination: fail
    default_destination: waffles_default
    verbose: True
'''

iv91dict = {
    'tools': {
        'spades': {
            'rules': [
                {
                    'lower_bound': 0,
                    'nice_value': 0,
                    'rule_type': 'file_size',
                    'upper_bound': 0,
                    'destination': 'fail',
                    'fail_message': "Invalid parameters for rule 1 in 'spades'."
                }
            ]
        }
    },
    'default_destination': "waffles_default"
}

# Tool default fail no destination
ivYMLTest11 = '''
    tools:
      spades:
        rules:
          - rule_type: file_size
            nice_value: -21
            lower_bound: 1 KB
            upper_bound: Infinity
            destination: waffles_low
        default_destination: waffles_low
    default_destination: waffles_default
    verbose: True
'''

# Arguments fail no fail_message
ivYMLTest12 = """
    tools:
      spades:
        rules:
          - rule_type: arguments
            nice_value: 0
            arguments:
              careful: true
            destination: fail
    default_destination: waffles_default
    verbose: True
"""

iv12dict = {
    "tools": {
        "spades": {
            "rules": [
                {
                    "rule_type": "arguments",
                    'nice_value': 0,
                    "arguments": {
                        "careful": True,
                    },
                    "destination": "fail",
                    "fail_message": "Invalid parameters for rule 1 in 'spades'."
                }
            ]
        }
    },
    'default_destination': "waffles_default"
}

# Arguments fail no arguments
ivYMLTest131 = """
    tools:
      spades:
        rules:
          - rule_type: arguments
            nice_value: 0
            fail_message: Something went wrong
            destination: fail
    default_destination: waffles_default
    verbose: True
"""

iv131dict = {
    'default_destination': "waffles_default"
}

# Arguments fail no destination
ivYMLTest132 = """
    tools:
      spades:
        rules:
          - rule_type: arguments
            nice_value: 0
            fail_message: Something went wrong
            arguments:
              careful: true
    default_destination: waffles_default
    verbose: True
"""

iv132dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'arguments': {
                        'careful': True
                    },
                    'rule_type': 'arguments',
                    'destination': 'fail',
                    'fail_message': 'Something went wrong',
                    'nice_value': 0
                }
            ]
        }
    }
}

# Multiple rules in 1 job, first one failing
ivYMLTest133 = '''
    tools:
      smalt:
        rules:
          - rule_type: file_size
            nice_value: 0
            lower_bound: 0
            upper_bound: 100000000
            destination: fail
          - rule_type: file_size
            nice_value: 0
            lower_bound: 100000000
            upper_bound: Infinity
            destination: waffles_low_4
    default_destination: waffles_low
    verbose: True
'''

iv133dict = {
    "tools": {
        "smalt": {
            "rules": [
                {
                    "rule_type": "file_size",
                    'nice_value': 0,
                    "lower_bound": 0,
                    "upper_bound": 100000000,
                    "fail_message": "Invalid parameters for rule 1 in 'smalt'.",
                    "destination": "fail"
                }, {
                    "rule_type": "file_size",
                    'nice_value': 0,
                    "lower_bound": 100000000,
                    "upper_bound": "Infinity",
                    "destination": "waffles_low_4"
                }
            ]
        }
    },
    'default_destination': "waffles_low"
}

# No destination and no fail_message
ivYMLTest134 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            upper_bound: 10000
            lower_bound: 0
            nice_value: 0
    default_destination: waffles_default
    verbose: True
"""

iv134dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'rule_type': 'file_size',
                    'upper_bound': 10000,
                    'lower_bound': 0,
                    'nice_value': 0
                }
            ]
        }
    }
}

# Reversed upper and lower bounds
ivYMLTest135 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            upper_bound: 100
            lower_bound: 200
            nice_value: 0
            destination: waffles_low_4
    default_destination: waffles_default
    verbose: True
"""

iv135dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'rule_type': 'file_size',
                    'upper_bound': 200,
                    'lower_bound': 100,
                    'nice_value': 0,
                    'destination': 'waffles_low_4'
                }
            ]
        }
    }
}

# Tool has rules category but no rules, and no tool-specific default destination
ivYMLTest136 = """
    tools:
      spades:
        rules:

    default_destination: waffles_default
    verbose: True
"""

iv136dict = {
    'default_destination': 'waffles_default'
}

# Tool is blank; no tool-specific default destination, no rules category
ivYMLTest137 = """
    tools:
      spades:

    default_destination: waffles_default
    verbose: True
"""

iv137dict = {
    'default_destination': 'waffles_default'
}

# Tool specifies authorized users with an invalid entry
ivYMLTest138 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            upper_bound: 200
            lower_bound: 100
            nice_value: 0
            destination: waffles_low_4
            users:
              - validuser@email.com
              - invaliduser.email@com
              - 123
    default_destination: waffles_default
    verbose: True
"""

iv138dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'rule_type': 'file_size',
                    'upper_bound': 200,
                    'lower_bound': 100,
                    'nice_value': 0,
                    'destination': 'waffles_low_4',
                    'users': [
                        'validuser@email.com'
                    ]
                }
            ]
        }
    }
}

# Tool does not specify list under users
ivYMLTest139 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            upper_bound: 600
            lower_bound: 200
            nice_value: 0
            destination: waffles_high
          - rule_type: file_size
            upper_bound: 199
            lower_bound: 100
            nice_value: 0
            destination: waffles_low_4
            users:
    default_destination: waffles_default
    verbose: True
"""

iv139dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'rule_type': 'file_size',
                    'upper_bound': 600,
                    'lower_bound': 200,
                    'nice_value': 0,
                    'destination': 'waffles_high'
                }
            ]
        }
    }
}

# Tool supplies only invalid users
ivYMLTest140 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            upper_bound: 600
            lower_bound: 200
            nice_value: 0
            destination: waffles_high
          - rule_type: file_size
            upper_bound: 199
            lower_bound: 100
            nice_value: 0
            destination: waffles_low_4
            users:
                - invalid.user1@com
                - invalid.user2@com
    default_destination: waffles_default
    verbose: True
"""

iv140dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'rule_type': 'file_size',
                    'upper_bound': 600,
                    'lower_bound': 200,
                    'nice_value': 0,
                    'destination': 'waffles_high'
                }
            ]
        }
    }
}

# Tool supplies users list, but empty
ivYMLTest141 = """
    tools:
      spades:
        rules:
          - rule_type: file_size
            upper_bound: 600
            lower_bound: 200
            nice_value: 0
            destination: waffles_high
          - rule_type: file_size
            upper_bound: 199
            lower_bound: 100
            nice_value: 0
            destination: waffles_low_4
            users:
                -
                -
    default_destination: waffles_default
    verbose: True
"""

iv141dict = {
    'default_destination': 'waffles_default',
    'tools': {
        'spades': {
            'rules': [
                {
                    'rule_type': 'file_size',
                    'upper_bound': 600,
                    'lower_bound': 200,
                    'nice_value': 0,
                    'destination': 'waffles_high'
                }
            ]
        }
    }
}

# Bad bounds setup for num_input_datasets
ivYMLTest142 = '''
    tools:
      smalt:
        rules:
          - rule_type: num_input_datasets
            nice_value: 0
            lower_bound: Infinity
            upper_bound: 200
            destination: cluster_low_4
    default_destination: waffles_low
    verbose: True
'''

iv142dict = {
    'default_destination': 'waffles_low',
    'tools': {
        'smalt': {
            'rules': [
                {
                    'rule_type': 'num_input_datasets',
                    'upper_bound': 200,
                    'lower_bound': 0,
                    'nice_value': 0,
                    'destination': 'cluster_low_4'
                }
            ]
        }
    }
}

# Even worse bounds setup for num_input_datasets
ivYMLTest143 = '''
    tools:
      smalt:
        rules:
          - rule_type: num_input_datasets
            nice_value: 0
            lower_bound: Infinity
            upper_bound: Infinity
            destination: cluster_low_4
    default_destination: waffles_low
    verbose: True
'''

iv143dict = {
    'default_destination': 'waffles_low',
    'tools': {
        'smalt': {
            'rules': [
                {
                    'rule_type': 'num_input_datasets',
                    'upper_bound': 'Infinity',
                    'lower_bound': 0,
                    'nice_value': 0,
                    'destination': 'cluster_low_4'
                }
            ]
        }
    }
}

# No med priority destination in default destination
ivYMLTest144 = '''
    default_destination:
      priority:
        low: waffles_low
    verbose: True
'''

# invalid priority destination in default destination
ivYMLTest145 = '''
    default_destination:
      priority:
        med: waffles_low
        mine: waffles_low
    verbose: True
'''

# No med priority destination in tool config
ivYMLTest146 = '''
    tools:
      smalt:
        rules:
          - rule_type: num_input_datasets
            nice_value: 0
            lower_bound: 0
            upper_bound: Infinity
            destination:
              priority:
                low: cluster_low_4
    default_destination:
      priority:
        med: waffles_low
    verbose: True
'''

# Invalid priority destination in tool config
ivYMLTest147 = '''
    tools:
      smalt:
        rules:
          - rule_type: num_input_datasets
            nice_value: 0
            lower_bound: 0
            upper_bound: Infinity
            destination:
              priority:
                med: cluster_med_4
                mine: cluster_low_4
    default_destination:
      priority:
        med: waffles_low
    verbose: True
'''

# invalid priority in users section
ivYMLTest148 = '''
    default_destination:
      priority:
        med: waffles_low
    users:
      user@email.com:
        priority: mine
    verbose: True
'''
