#
#   Object running the combination routines when running in GUI mode.
#   This object will be run as a sub-thread to leave the UI responsive, both so that
#   Mouse and window responds and so that the user can click a Cancel button up there
#   to stop a long-running process.  There is no good "thread cancel" signal in Python
#   so the "cancel" is implemented by setting a flag which is periodically polled in this thread.
#

from PyQt5.QtCore import QObject, pyqtSignal

import MasterMakerExceptions
from ConsoleCallback import ConsoleCallback
from DataModel import DataModel
from FileCombiner import FileCombiner
from FileDescriptor import FileDescriptor
from SessionController import SessionController


class CombineThreadWorker(QObject):

    #   Signals emitted from the thread

    finished = pyqtSignal()             # Tell interested parties that we are finished
    console_line = pyqtSignal(str)      # Add a line to the console object in the UI
    remove_from_ui = pyqtSignal(str)    # Remove given file (full path) from the UI table

    def __init__(self, data_model: DataModel,
                 descriptors: [FileDescriptor],
                 output_path: str,
                 session_controller: SessionController):
        """
        Initialize the combine-thread-worker object
        :param data_model:          Data Model giving all the relevant options for this job
        :param descriptors:         List of files to be combined
        :param output_path:         Absolute path name where combined result is to go
        :param session_controller:  Session controller for this subtask
        """
        QObject.__init__(self)
        self._data_model = data_model
        self._descriptors = descriptors
        self._output_path = output_path
        self._session_controller = session_controller

    def run_combination_session(self):
        """
        Run the file-combination session represented by this object
        """
        # Create a console output object.  This is passed in to the various math routines
        # to allow them to output progress.  We use this indirect method of getting progress
        # so that it can go to the console window in this case, but the same worker code can send
        # progress lines to the standard system output when being run from the command line
        console = ConsoleCallback(self.console_callback)

        console.message("Starting session", 0)
        file_combiner = FileCombiner(self._session_controller, self.file_moved_callback)

        # Do actual work
        try:
            # Are we using grouped processing?
            if self._data_model.get_group_by_size() \
                    or self._data_model.get_group_by_temperature():
                file_combiner.process_groups(self._data_model, self._descriptors,
                                                             self._output_path,
                                                             console)
            else:
                # Not grouped, producing a single output file. Get output file location
                file_combiner.original_non_grouped_processing(self._descriptors, self._data_model,
                                                                              self._output_path,
                                                                              console)
        except FileNotFoundError as exception:
            self.error_dialog("File not found", f"File \"{exception.filename}\" not found or not readable")
        except MasterMakerExceptions.NoGroupOutputDirectory as exception:
            self.error_dialog("Group Directory Missing",
                              f"The specified output directory \"{exception.get_directory_name()}\""
                              f" does not exist and could not be created.")
        except MasterMakerExceptions.NotAllBiasFrames:
            self.error_dialog("The selected files are not all Bias Frames",
                              "If you know the files are bias frames, they may not have proper FITS data "
                              "internally. Check the \"Ignore FITS file type\" box to proceed anyway.")
        except MasterMakerExceptions.IncompatibleSizes:
            self.error_dialog("The selected files can't be combined",
                              "To be combined into a master file, the files must have identical X and Y "
                              "dimensions, and identical Binning values.")
        except PermissionError as exception:
            self.error_dialog("Unable to write file",
                              f"The specified output file, "
                              f"\"{exception.filename}\","
                              f" cannot be written or replaced: \"permission error\"")
        except MasterMakerExceptions.SessionCancelled:
            self.console_callback("*** Session cancelled ***")

        self.finished.emit()

    #
    #   The console object has produced a line it would like displayed.  We'll emit it as a signal
    #   from this sub-thread, so it can be picked up by the main thread and displayed in the console
    #   frame in the user interface.
    #
    def console_callback(self, message: str):
        """
        The console object has produced a line it would like displayed.  We'll emit it as a signal
        from this sub-thread, so it can be picked up by the main thread and displayed in the console
        frame in the user interface.
        :param message:     Message to be written to the command line or console window
        """
        self.console_line.emit(message)

    #
    #   Error message from an exception.  Put it on the console
    #
    def error_dialog(self, short_message: str, long_message: str):
        """
        Display an error message from an exceptionon the console, with suitable formatting
        :param short_message:       Brief description of the problem
        :param long_message:        Longer explanatory text when it is available
        """
        self.console_callback("*** ERROR *** " + short_message + ": " + long_message)

    #
    #   Method that is called back when a file is moved after being processed
    #   Send this information back to the main task by emitting a signal.
    #   This allows us to remove it from the user interface, since the path will no longer be valid
    #

    def file_moved_callback(self, file_moved_from_path: str):
        """
        Method that is called back when a file is moved after being processed
        Send this information back to the main task by emitting a signal.
        This allows us to remove it from the user interface, since the path will no longer be valid

        :param file_moved_from_path:    Where *was* the file that we just moved?
        """
        self.remove_from_ui.emit(file_moved_from_path)
