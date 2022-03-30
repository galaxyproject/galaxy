""" brew_exts defines generic extensions to Homebrew this file
builds on those abstraction and provides Galaxy specific functionality
not useful to the brew external commands.
"""
from ..deps import brew_exts

DEFAULT_TAP = "homebrew/science"


class HomebrewRecipe:
    def __init__(self, recipe, version, tap):
        self.recipe = recipe
        self.version = version
        self.tap = tap


def requirements_to_recipes(requirements):
    return filter(None, map(requirement_to_recipe, requirements))


def requirement_to_recipe(requirement):
    if requirement.type != "package":
        return None
    # TOOD: Allow requirements to annotate optionalbrew specific
    # adaptions.
    recipe_name = requirement.name
    recipe_version = requirement.version
    return HomebrewRecipe(recipe_name, recipe_version, tap=DEFAULT_TAP)


def requirements_to_recipe_contexts(requirements, brew_context):
    def to_recipe_context(homebrew_recipe):
        return brew_exts.RecipeContext(homebrew_recipe.recipe, homebrew_recipe.version, brew_context)

    return map(to_recipe_context, requirements_to_recipes(requirements))
