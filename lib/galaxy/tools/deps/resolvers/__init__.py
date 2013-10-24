from abc import ABCMeta, abstractmethod


class DependencyResolver( object ):
    __metaclass__ = ABCMeta

    @abstractmethod
    def resolve( self, name, version, type, **kwds ):
        """
        Given inputs describing dependency in the abstract, yield tuple of
        (script, bin, version). Here script is the env.sh file to source
        before running a job, if that is not found the bin directory will be
        appended to the path (if it is not None). Finally, version is the
        resolved tool dependency version (which may differ from requested
        version for instance if the request version is 'default'.)
        """


class Dependency( object ):
    __metaclass__ = ABCMeta

    @abstractmethod
    def shell_commands( self, requirement ):
        """
        Return shell commands to enable this dependency.
        """


class NullDependency( Dependency ):

    def shell_commands( self, requirement ):
        return None

INDETERMINATE_DEPENDENCY = NullDependency()
