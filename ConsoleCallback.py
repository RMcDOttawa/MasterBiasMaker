from typing import Callable

from Console import Console


#
#   A console handler that produces output by sending the desired message to
#   a callback method that was provided at creation time
#
class ConsoleCallback(Console):

    def __init__(self, output_callback: Callable[[str], None]):
        """
        Initialize this object by remembering the callback function for output messages
        :param output_callback:     Function to be called to output a message
        """
        Console.__init__(self)
        self._output_callback = output_callback

    def output_message(self, message: str):
        """
        Put the given message on the console via the stored callback function
        :param message:     Message to be displayed.
        """
        self._output_callback(message)
