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
        self.ui.installEventFilter(self)

    # Catch window resizing so we can record the changed size

    def eventFilter(self, triggering_object: QObject, event: QEvent) -> bool:
        """Event filter, looking for window resize events so we can remember the new size"""
        if isinstance(event, QResizeEvent):
            window_size = event.size()
            self._preferences.set_console_window_size(window_size)
        # elif isinstance(event,QMoveEvent):
        #     new_position = event.pos()
        #     self._preferences.set_console_window_position(new_position)
        return False  # Didn't handle event

    def worker_thread_finished(self):
        self._qthread.quit()
        self.buttons_active_state(False)

    def add_to_console(self, message: str):
        self._signal_mutex.lock()
        # Create the text line to go in the console
        list_item: QListWidgetItem = QListWidgetItem(message)

        # Add to bottom of console and scroll to it
        self.ui.consoleList.addItem(list_item)
        self.ui.consoleList.scrollToItem(list_item)
        self._signal_mutex.unlock()

    def buttons_active_state(self, active: bool):
        self.ui.cancelButton.setEnabled(active)
        self.ui.closeButton.setEnabled(not active)

    def cancel_button_clicked(self):
        self.add_to_console("Cancelling....")
        self._session_controller.cancel_thread()

    def close_button_clicked(self):
        self.ui.close()

    def remove_from_ui(self, path_to_remove: str):
        self._disposed_callback(path_to_remove)
