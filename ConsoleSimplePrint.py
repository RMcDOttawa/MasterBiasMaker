from Console import Console


#
#   A console handler that produces output by simply printing it to standard output
#   Why the complexity?  Because there is another instance, also a subclass of Console,
#   that produces the output across a thread boundary by emitting a signal.  This version
#   is used during command-line execution, which is a single-thread operation. This use
#   of console subclasses means the combination math routines can produce console output without
#   concern of whether they are running as the sub task with console window or the command line
#
class ConsoleSimplePrint(Console):

    def __init__(self):
        Console.__init__(self)

    def output_message(self, message: str):
        print(message)
