#
#   Custom exceptions that are used to indicate some problem, discovered deep in a processing loop,
#   to the outer-level control loop.  We use the built-in Python exceptions whenever possible,
#   and the following custom exceptions when necessary
#

#
#   Group processing is selected, which puts created files in a directory
#   The specified directory does not exist
#


class NoGroupOutputDirectory(Exception):
    def __init__(self, directory_name: str):
        self._directory_name = directory_name

    def get_directory_name(self) -> str:
        return self._directory_name

#
#   The selected files are not all Bias frames and "ignore type" option is not selected
#


class NotAllBiasFrames(Exception):
    pass

#
#   Files to be combined have different dimensions or binning
#


class IncompatibleSizes(Exception):
    pass


class TestException(Exception):
    pass


class SessionCancelled(Exception):
    pass
