#
#   Object to take a message and put it on the console.  Where that goes will be different
#   in the command-line and GUI versions
#
#   Messages can be indented.  Current indentation level can be saved on a stack,
#   incremented in the messaging call, and restored from the stack
#
from datetime import datetime

from Constants import Constants


class Console:

    def __init__(self):
        self._message_level = 0
        self._message_level_stack: [int] = []

    #
    #   Put a message on the console.
    #   Change the indentation level by the given increment, which can only be
    #	+1, -1, or 0 (i.e. indent, outdent, or no-dent)
    #   If temp=True, reset it immediately after
    #
    def message(self, message: str,
                level_change: int,
                temp: bool = False):
        """
        Put a message on the console.
        Change the indentation level by the given increment, which can only be
        +1, -1, or 0 (i.e. indent, outdent, or no-dent)
        If temp=True, reset it immediately after

        :param message:         String to be displayed
        :param level_change:    Change to indentation level (-1, 0, or +1)
        :param temp:            Flag if the indentation level change is temporary (this message only)
        """
        assert -1 <= level_change <= 1
        self._message_level += level_change
        indent_string = " " * ((self._message_level - 1) * Constants.CONSOLE_INDENTATION_SIZE)
        time_string = datetime.now().strftime("%H:%M:%S")
        # The following must be implemented in a subclass. That subclass decides where to actually
        # put the console line:  a window, the system standard output, etc
        self.output_message(time_string + " " + indent_string + message)
        if temp:
            self._message_level -= level_change

    #   Save the current indentation level on a push-down stack for easy restoration
    def push_level(self):
        """
        Save the current indentation level on a push-down stack for easy restoration
        """
        self._message_level_stack.append(self._message_level)

    #   Pop the saved indentation level off the top of the push-down stack
    def pop_level(self):
        """
        Pop the saved indentation level off the top of the push-down stack
        """
        assert len(self._message_level_stack) > 0
        self._message_level = self._message_level_stack.pop()

    #   We're done an operation that is supposed to be balanced.  If the stack is not empty
    #   we've made an error, cause a traceback so we can track it.
    def verify_done(self):
        """
        We're finished with operation that is supposed to be balanced with respect to console indentation.
        If the stack is not empty we've made an error, cause a traceback so we can track it.
        :return:
        """
        assert len(self._message_level_stack) == 0

    #   Return the size of the stack, to help users track mismatched push/pop
    def get_stack_size(self):
        """
        Return the size of the stack, to help users track mismatched push/pop
        :return:        Integer, number of items on the stack
        """
        return len(self._message_level_stack)

    def output_message(self, param):
        print("pseudo-abstract class Console, message should not have been called")
        assert False
