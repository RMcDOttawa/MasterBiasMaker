from typing import Callable

from Console import Console


#
#   A console handler that produces output by sending the desired message to
#   a callback method that was provided at creation time
#
class ConsoleCallback(Console):

    def __init__(self, output_callback: Callable[[str], None]):
        Console.__init__(self)
        self._output_callback = output_callback

    def output_message(self, message: str):
        self._output_callback(message)
