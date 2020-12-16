# Utilities to help program run on multiple OS - for now, windows and mac
# Helps locate resource files, end-running around the problems I've been having
# with the various native bundle packaging utilities that I can't get working
import os


class MultiOsUtil:

    # Generate a file's full path, given the file name, and having the
    # file reside in the same directory where the running program resides

    @classmethod
    def path_for_file_in_program_directory(cls, file_name: str) -> str:
        """
        Determine full absolute path to a file located in the program directory
        :param file_name:   Base file name
        :return:            Full path situating that file name in the program directory
        """
        program_full_path = os.path.realpath(__file__)
        directory_name = os.path.dirname(program_full_path)
        path_to_file = f"{directory_name}/{file_name}"
        return path_to_file

