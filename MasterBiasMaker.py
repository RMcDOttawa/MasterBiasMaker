#!/Library/Frameworks/Python.framework/Versions/3.8/bin/python3.8
import sys
from argparse import ArgumentParser

from PyQt5 import QtWidgets

from CommandLineHandler import CommandLineHandler
from DataModel import DataModel
from MainWindow import MainWindow
# First phase in development of automated calibration frame combination.
# This program combines Bias Frames into a master bias.  If run without parameters, a GUI
# window opens.  If run given a list of file names as args, then those are immediately processed
# without the UI interaction.  Preferences control how they are combined and where the result goes.
from Preferences import Preferences

# Set up command line arguments
arg_parser = ArgumentParser(description="Combine Bias-Frame FITS files into a master bias")
arg_parser.add_argument("-g", "--gui", action="store_true",
                        help="Force GUI interface to open, ignoring other arguments")

# combination algorithm options - only one may be used
method_arg_group = arg_parser.add_mutually_exclusive_group()
method_arg_group.add_argument("-m", "--mean", action="store_true",
                              help="Combine by simple mean")
method_arg_group.add_argument("-n", "--median", action="store_true",
                              help="Combine by simple median")
method_arg_group.add_argument("-mm", "--minmax", type=int, metavar="<# values to clip>",
                              help="Min-max clipping of <n> values, then mean")
method_arg_group.add_argument("-s", "--sigma", type=float, metavar="<z threshold>",
                              help="Remove values with z-score greater than threshold, then mean")

# Grouping
arg_parser.add_argument("-gs", "--groupsize", action="store_true",
                              help="Group files by size (dimensions and binning)")
arg_parser.add_argument("-gt", "--grouptemperature", type=float, metavar="<Group by temperature with bandwidth>",
                              help="Group by temperature with given bandwidth")
arg_parser.add_argument("-mg", "--minimumgroup", type=int, metavar="<Minimum group size>",
                              help="Ignore groups smaller than given size")
arg_parser.add_argument("-od", "--outputdirectory", type=str, metavar="Output directory",
                        help="Directory to receive outputs of grouped combines")

# File disposition and other options
arg_parser.add_argument("-v", "--moveinputs", metavar="<directory>",
                        help="After successful processing, move input files to directory")
arg_parser.add_argument("-t", "--ignoretype", action="store_true",
                        help="Ignore the internal FITS file type (flat, dark, bias, etc)")
arg_parser.add_argument("-o", "--output", metavar="<output path>",
                        help="Name of output file (default: constructed name at location of inputs)")

arg_parser.add_argument("filenames", nargs="*")
args = arg_parser.parse_args()

preferences: Preferences = Preferences()
data_model: DataModel = DataModel(preferences)

# If no arguments were given, or if the --gui argument was given, open the GUI window
if len(sys.argv) == 1 or args.gui:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(preferences, data_model)
    window.set_up_ui()
    window.ui.show()
    app.exec_()
else:
    # We're operating in pure command-line mode
    command_line_handler = CommandLineHandler(args, data_model)
    command_line_handler.execute()
