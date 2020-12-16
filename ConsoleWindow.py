#
#   Window containing a console pane, used to display output messages in the GUI version.
#   (In the command-line version such messages are simply written to standard output)
#
from typing import Callable

from PyQt5 import uic
from PyQt5.QtCore import QThread, QMutex, QObject, QEvent
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import QDialog, QListWidgetItem

from CombineThreadWorker import CombineThreadWorker
from DataModel import DataModel
from FileDescriptor import FileDescriptor
from MultiOsUtil import MultiOsUtil
from Preferences import Preferences
from SessionController import SessionController


class ConsoleWindow(QDialog):
    def __init__(self,
                 preferences: Preferences,
                 data_model: DataModel,
                 descriptors: [FileDescriptor],
                 output_path: str,
                 disposed_callback: Callable[[str], None]):
        """
        Initialize this object with needed data
        :param preferences:         The program's Preferences object
        :param data_model:          The data model for the current combination run
        :param descriptors:         Descriptors of all the files being processed
        :param output_path:         Path to receive output file(s)
        :param disposed_callback:   Method to call when this window is disposed, for cleanup
        """
        QDialog.__init__(self)
        self._disposed_callback = disposed_callback
        self._data_model = data_model
        self._descriptors = descriptors
        self._output_path = output_path
        self._preferences = preferences
        # Mutex to serialize signal handling from thread
        self._signal_mutex = QMutex()
        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("ConsoleWindow.ui"))

        # If a window size is saved, set the window size
        window_size = self._preferences.get_console_window_size()
        if window_size is not None:
            self.ui.resize(window_size)

        # Responders
        self.ui.cancelButton.clicked.connect(self.cancel_button_clicked)
        self.ui.closeButton.clicked.connect(self.close_button_clicked)

        self.buttons_active_state(False)

        # Create thread to run the processing
        self._session_controller: SessionController = SessionController()
        self._worker_object = CombineThreadWorker(self._data_model, descriptors, output_path, self._session_controller)

        # Create and run the processing thread
        self._qthread = QThread()
        self._worker_object.moveToThread(self._qthread)

        # Have the thread-started signal invoke the actual worker object
        self._qthread.started.connect(self._worker_object.run_combination_session)

        # Have the worker finished signal tell the thread to quit
        # self._worker_object.finished.connect(self._qthread.quit)
        self._worker_object.finished.connect(self.worker_thread_finished)

        # Other signals of interest
        self._worker_object.console_line.connect(self.add_to_console)
        self._worker_object.remove_from_ui.connect(self.remove_from_ui)

        # Properly enable buttons (cancel and close) and start the worker thread
        self.buttons_active_state(True)
        self._qthread.start()

    def set_up_ui(self):
        """
        Set up the UI for this console window by installing an event filter that will
        catch repositioning or resizing of the window, so we can remember that for future use.
        :return:
        """
        self.ui.installEventFilter(self)

    # Catch window resizing so we can record the changed size

    def eventFilter(self, triggering_object: QObject, event: QEvent) -> bool:
        """
        Catch window resizing so we can record the changed size.   Note this is called for
        all events, so we must check if it's a resize event and quickly pass on others
        :param triggering_object:       System object triggering the event
        :param event:                   Event we're inspecting
        :return:                        Always "False" indicating we didn't handle the event - it is still needed
        """
        if isinstance(event, QResizeEvent):
            window_size = event.size()
            self._preferences.set_console_window_size(window_size)
        # elif isinstance(event,QMoveEvent):
        #     new_position = event.pos()
        #     self._preferences.set_console_window_position(new_position)
        return False  # Didn't handle event

    def worker_thread_finished(self):
        """
        Method called when the subtask is finished, so we can clean it up and restore the
        window buttons (e.g. "Cancel") to their normal state.
        """
        self._qthread.quit()
        self.buttons_active_state(False)

    def add_to_console(self, message: str):
        """
        Add given line of text to the console pane in the current window, scrolling to ensure it is in view.
        Since these requests are coming from a subtask, the window update is done as a thread-locked block.
        :param message:     Text to be added to console
        """
        self._signal_mutex.lock()
        # Create the text line to go in the console
        list_item: QListWidgetItem = QListWidgetItem(message)

        # Add to bottom of console and scroll to it
        self.ui.consoleList.addItem(list_item)
        self.ui.consoleList.scrollToItem(list_item)
        self._signal_mutex.unlock()

    def buttons_active_state(self, active: bool):
        """
        Set window buttons to the appropriate state for when the subtask is active.  i.e. when the subtask
        is running, we allow Cancel but don't allow any other button clicks; when the subtask is not running
        we allow other button clicks but not Cancel.
        :param active:      Whether subtask is running
        """
        self.ui.cancelButton.setEnabled(active)
        self.ui.closeButton.setEnabled(not active)

    def cancel_button_clicked(self):
        """Cancel button has been clicked.  Note that on the console, and cancel the subtask."""
        self.add_to_console("Cancelling....")
        self._session_controller.cancel_thread()

    def close_button_clicked(self):
        """Close Button, which simply closes the current window"""
        self.ui.close()

    def remove_from_ui(self, path_to_remove: str):
        """Catch the fact that the window has been closed and inform other interested parties"""
        self._disposed_callback(path_to_remove)
