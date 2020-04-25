# Class with an instance shared by the main event controller and the session worker
# Using mutex-lock, basic status such as "cancel the thread" can be set by the main controller
# and safely read and responded to by the worker.
from PyQt5.QtCore import QMutex


class SessionController:

    def __init__(self):
        self._mutex = QMutex()
        self._thread_ok_to_run = True

    def cancel_thread(self):
        """Set flag to cancel the controlled thread"""
        self._mutex.lock()
        self._thread_ok_to_run = False
        self._mutex.unlock()

    def thread_running(self):
        """Indicate if the controlled thread is still running"""
        self._mutex.lock()
        result = self._thread_ok_to_run
        self._mutex.unlock()
        return result

    def thread_cancelled(self):
        """Indicate if the controlled thread is cancelled"""
        return not self.thread_running()

