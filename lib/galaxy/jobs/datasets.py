"""
Utility classes allowing Job interface to reason about datasets.
"""
import os.path

from abc import ABCMeta
from abc import abstractmethod


def dataset_path_rewrites( dataset_paths ):
    dataset_paths_with_rewrites = filter( lambda path: getattr( path, "false_path", None ), dataset_paths )
    return dict( [ ( dp.real_path, dp ) for dp in dataset_paths_with_rewrites ] )


class DatasetPath( object ):

    def __init__(
        self,
        dataset_id,
        real_path,
        false_path=None,
        false_extra_files_path=None,
        mutable=True
    ):
        self.dataset_id = dataset_id
        self.real_path = real_path
        self.false_path = false_path
        self.false_extra_files_path = false_extra_files_path
        self.mutable = mutable

    def __str__( self ):
        if self.false_path is None:
            return self.real_path
        else:
            return self.false_path

    def with_path_for_job( self, false_path, false_extra_files_path=None ):
        """
        Clone the dataset path but with a new false_path.
        """
        dataset_path = self
        if false_path is not None:
            dataset_path = DatasetPath(
                dataset_id=self.dataset_id,
                real_path=self.real_path,
                false_path=false_path,
                false_extra_files_path=false_extra_files_path,
                mutable=self.mutable,
            )
        return dataset_path


class DatasetPathRewriter( object ):
    """ Used by runner to rewrite paths. """
    __metaclass__ = ABCMeta

    @abstractmethod
    def rewrite_dataset_path( self, dataset, dataset_type ):
        """
        Dataset type is 'input' or 'output'.
        Return None to indicate not to rewrite this path.
        """


class NullDatasetPathRewriter( object ):
    """ Used by default for jobwrapper, do not rewrite anything.
    """

    def rewrite_dataset_path( self, dataset, dataset_type ):
        """ Keep path the same.
        """
        return None


class OutputsToWorkingDirectoryPathRewriter( object ):
    """ Rewrites all paths to place them in the specified working
    directory for normal jobs when Galaxy is configured with
    app.config.outputs_to_working_directory. Job runner base class
    is responsible for copying these out after job is complete.
    """

    def __init__( self, working_directory ):
        self.working_directory = working_directory

    def rewrite_dataset_path( self, dataset, dataset_type ):
        """ Keep path the same.
        """
        if dataset_type == 'output':
            false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % dataset.id ) )
            return false_path
        else:
            return None


class TaskPathRewriter( object ):
    """ Rewrites all paths to place them in the specified working
    directory for TaskWrapper. TaskWrapper is responsible for putting
    them there and pulling them out.
    """

    def __init__( self, working_directory, job_dataset_path_rewriter ):
        self.working_directory = working_directory
        self.job_dataset_path_rewriter = job_dataset_path_rewriter

    def rewrite_dataset_path( self, dataset, dataset_type ):
        """
        """
        dataset_file_name = dataset.file_name
        job_file_name = self.job_dataset_path_rewriter.rewrite_dataset_path( dataset, dataset_type ) or dataset_file_name
        return os.path.join( self.working_directory, os.path.basename( job_file_name ) )
