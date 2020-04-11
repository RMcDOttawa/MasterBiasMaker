import numpy
from PyQt5 import uic
from PyQt5.QtCore import QObject, QEvent, QModelIndex
from PyQt5.QtWidgets import QMainWindow, QDialog, QHeaderView, QFileDialog, QMessageBox

from CommandLineHandler import CommandLineHandler
from Constants import Constants
from FileDescriptor import FileDescriptor
from FitsFileTableModel import FitsFileTableModel
from MultiOsUtil import MultiOsUtil
from Preferences import Preferences
from PreferencesWindow import PreferencesWindow
from RmFitsUtil import RmFitsUtil
from SharedUtils import SharedUtils
from Validators import Validators


class MainWindow(QMainWindow):

    def __init__(self, preferences: Preferences):
        """Initialize MainWindow class"""
        self._preferences = preferences
        QMainWindow.__init__(self)
        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("MainWindow.ui"))
        self._field_validity: {object, bool} = {}
        self._table_model: FitsFileTableModel

        # Load algorithm from preferences

        algorithm = preferences.get_master_combine_method()
        if algorithm == Constants.COMBINE_MEAN:
            self.ui.combineMeanRB.setChecked(True)
        elif algorithm == Constants.COMBINE_MEDIAN:
            self.ui.combineMedianRB.setChecked(True)
        elif algorithm == Constants.COMBINE_MINMAX:
            self.ui.combineMinMaxRB.setChecked(True)
        else:
            assert (algorithm == Constants.COMBINE_SIGMA_CLIP)
            self.ui.combineSigmaRB.setChecked(True)

        self.ui.minMaxNumDropped.setText(str(preferences.get_min_max_number_clipped_per_end()))
        self.ui.sigmaThreshold.setText(str(preferences.get_sigma_clip_threshold()))

        # Load disposition from preferences

        disposition = preferences.get_input_file_disposition()
        if disposition == Constants.INPUT_DISPOSITION_SUBFOLDER:
            self.ui.dispositionSubFolderRB.setChecked(True)
        else:
            assert (disposition == Constants.INPUT_DISPOSITION_NOTHING)
            self.ui.dispositionNothingRB.setChecked(True)
        self.ui.subFolderName.setText(preferences.get_disposition_subfolder_name())

        # Set up the file table
        self._table_model = FitsFileTableModel(self.ui.ignoreFileType.isChecked())
        self.ui.filesTable.setModel(self._table_model)
        # Columns should resize to best fit their contents
        self.ui.filesTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.connect_responders()

        # If a window size is saved, set the window size
        window_size = self._preferences.get_main_window_size()
        if window_size is not None:
            self.ui.resize(window_size)

        self.enable_fields()
        self.enable_buttons()

    # Connect UI controls to methods here for response
    def connect_responders(self):
        """Connect UI fields and controls to the methods that respond to them"""

        # Menu items
        self.ui.actionPreferences.triggered.connect(self.preferences_menu_triggered)
        self.ui.actionOpen.triggered.connect(self.pick_files_button_clicked)
        self.ui.actionSelectAll.triggered.connect(self.select_all_clicked)

        #  Responder for algorithm buttons
        self.ui.combineMeanRB.clicked.connect(self.algorithm_button_clicked)
        self.ui.combineMedianRB.clicked.connect(self.algorithm_button_clicked)
        self.ui.combineMinMaxRB.clicked.connect(self.algorithm_button_clicked)
        self.ui.combineSigmaRB.clicked.connect(self.algorithm_button_clicked)

        # Responders for algorithm fields
        self.ui.minMaxNumDropped.editingFinished.connect(self.min_max_drop_changed)
        self.ui.sigmaThreshold.editingFinished.connect(self.sigma_threshold_changed)

        # Responder for disposition buttons
        self.ui.dispositionNothingRB.clicked.connect(self.disposition_button_clicked)
        self.ui.dispositionSubFolderRB.clicked.connect(self.disposition_button_clicked)

        # Responder for disposition subfolder name
        self.ui.subFolderName.editingFinished.connect(self.sub_folder_name_changed)

        # Responder for "Pick Files" button
        self.ui.pickFilesButton.clicked.connect(self.pick_files_button_clicked)

        # React to changed selection in file table
        table_selection_model = self.ui.filesTable.selectionModel()
        table_selection_model.selectionChanged.connect(self.table_selection_changed)

        # Responders for select all and select none
        self.ui.selectAllButton.clicked.connect(self.select_all_clicked)
        self.ui.selectNoneButton.clicked.connect(self.select_none_clicked)

        # "Ignore file type" checkbox
        self.ui.ignoreFileType.clicked.connect(self.ignore_file_type_clicked)

        # Main "combine" button
        self.ui.combineSelectedButton.clicked.connect(self.combine_selected_clicked)

    # Certain initialization must be done after "__init__" is finished.
    def set_up_ui(self):
        """Perform initialization that requires class init to be finished"""
        # Catch events so we can see window resizing
        self.ui.installEventFilter(self)

    # Catch window resizing so we can record the changed size

    def eventFilter(self, triggering_object: QObject, event: QEvent) -> bool:
        """Event filter, looking for window resize events so we can remember the new size"""
        if event.type() == QEvent.Resize:
            window_size = event.size()
            self._preferences.set_main_window_size(window_size)
        return False  # Didn't handle event

    # "Ignore file type" button clicked.  Tell the data model the new value.
    def ignore_file_type_clicked(self):
        """Respond to clicking 'ignore file type' button"""
        self._table_model.set_ignore_file_type(self.ui.ignoreFileType.isChecked())

    # Select-all button has been clicked

    def select_all_clicked(self):
        """Select all the rows in the files table"""
        self.ui.filesTable.selectAll()

    # Select-None button has been clicked

    def select_none_clicked(self):
        """Clear the table selection, leaving no rows selected"""
        self.ui.filesTable.clearSelection()

    def algorithm_button_clicked(self):
        """ One of the algorithm buttons is clicked.  Change what fields are enabled"""
        self.enable_fields()
        self.enable_buttons()

    def disposition_button_clicked(self):
        """ One of the disposition buttons is clicked.  Change what fields are enabled"""
        self.enable_fields()
        self.enable_buttons()

    def min_max_drop_changed(self):
        """the field giving the number of minimum and maximum values to drop has been changed.
        Validate it (integer > 0) and store if valid"""
        proposed_new_number: str = self.ui.minMaxNumDropped.text()
        new_number = Validators.valid_int_in_range(proposed_new_number, 0, 256)
        valid = new_number is not None
        SharedUtils.background_validity_color(self.ui.minMaxNumDropped, valid)
        self._field_validity[self.ui.minMaxNumDropped] = valid
        self.enable_buttons()

    def sigma_threshold_changed(self):
        """the field giving the sigma limit beyond which values are ignored has changed
        Validate it (floating point > 0) and store if valid"""
        proposed_new_number: str = self.ui.sigmaThreshold.text()
        new_number = Validators.valid_float_in_range(proposed_new_number, 0.01, 100.0)
        valid = new_number is not None
        SharedUtils.background_validity_color(self.ui.sigmaThreshold, valid)
        self._field_validity[self.ui.sigmaThreshold] = valid
        self.enable_buttons()

    def sub_folder_name_changed(self):
        """the field giving the name of the sub-folder to be created or used has changed.
        Validate that it is an acceptable folder name and store if valid"""
        proposed_new_name: str = self.ui.subFolderName.text()
        # valid = Validators.valid_file_name(proposed_new_name, 1, 31)
        valid = SharedUtils.validate_folder_name(proposed_new_name)
        SharedUtils.background_validity_color(self.ui.subFolderName, valid)
        self._field_validity[self.ui.subFolderName] = valid
        self.enable_buttons()

    def enable_fields(self):
        """Enable text fields depending on state of various radio buttons"""

        # Enable Algorithm fields depending on which algorithm is selected
        self.ui.minMaxNumDropped.setEnabled(self.ui.combineMinMaxRB.isChecked())
        self.ui.sigmaThreshold.setEnabled(self.ui.combineSigmaRB.isChecked())

        # Enable Disposition fields depending on which disposition is selected
        self.ui.subFolderName.setEnabled(self.ui.dispositionSubFolderRB.isChecked())

    # Open a file dialog to pick files to be processed

    def pick_files_button_clicked(self):
        """'Pick Files' button or 'Open' menu item are selected.  Get the input files from the user."""
        dialog = QFileDialog()
        file_names, _ = QFileDialog.getOpenFileNames(dialog, "Pick Files", "",
                                                     f"FITS files(*.fit)",
                                                     # options=QFileDialog.ReadOnly | QFileDialog.DontUseNativeDialog)
                                                     options=QFileDialog.ReadOnly)
        if len(file_names) == 0:
            # User clicked "cancel"
            pass
        else:
            file_descriptions = self.make_file_descriptions(file_names)
            self._table_model.set_file_descriptors(file_descriptions)
        self.enable_buttons()

    def table_selection_changed(self):
        """Rows selected in the file table have changed; check for button enablement"""
        self.enable_buttons()

    def enable_buttons(self):
        """Enable buttons on the main window depending on validity and settings
        of other controls"""

        # "combineSelectedButton" is enabled only if
        #   - No text fields are in error state
        #   - At least one row in the file table is selected
        #   - If Min/Max algorithm selected with count "n", > 2n files selected
        #   - If sigma-clip algorithm selected, >= 3 files selected
        #   - If fixed precalibration file option selected, path must exist

        combine_enabled = self.all_text_fields_valid()
        selected = self.ui.filesTable.selectionModel().selectedRows()
        sigma_clip_enough_files = (not self.ui.combineSigmaRB.isChecked()) or len(selected) >= 3
        self.ui.combineSelectedButton.setEnabled(combine_enabled and len(selected) > 0
                                                 and self.min_max_enough_files(len(selected))
                                                 and sigma_clip_enough_files)

        # Enable select all and none only if rows in table
        any_rows = self._table_model.rowCount(QModelIndex()) > 0
        self.ui.selectNoneButton.setEnabled(any_rows)
        self.ui.selectAllButton.setEnabled(any_rows)

    def preferences_menu_triggered(self):
        """Respond to preferences menu by opening preferences dialog"""
        dialog: PreferencesWindow = PreferencesWindow()
        dialog.set_up_ui(self._preferences)
        QDialog.DialogCode = dialog.ui.exec_()

    def all_text_fields_valid(self):
        """Return whether all text fields are valid.  (In fact, returns that
        no text fields are invalid - not necessarily the same, since it is possible that
        a text field has not been tested.)"""
        all_fields_good = all(val for val in self._field_validity.values())
        return all_fields_good

    def make_file_descriptions(self, file_names: [str]) -> [FileDescriptor]:
        result: [FileDescriptor] = []
        for absolute_path in file_names:
            descriptor = RmFitsUtil.make_file_descriptor(absolute_path)
            result.append(descriptor)
        return result

    def combine_selected_clicked(self):
        # Get the list of selected files
        selected_files: [FileDescriptor] = self.get_selected_file_descriptors()
        assert len(selected_files) > 0  # Or else the button would have been disabled
        # Confirm that these are all bias frames, and can be combined (same binning and dimensions)
        if RmFitsUtil.all_compatible_sizes(selected_files):
            if self.ui.ignoreFileType.isChecked() \
                    or RmFitsUtil.all_of_type(selected_files, FileDescriptor.FILE_TYPE_BIAS):
                # Get output file location
                suggested_output_path = CommandLineHandler.create_output_path(selected_files[0],
                                                                              self.get_combine_method())
                output_file = self.get_output_file(suggested_output_path)
                if output_file is not None:
                    # Get (most common) filter name in the set
                    filter_name = SharedUtils.most_common_filter_name(selected_files)
                    # Do the combination
                    self.combine_files(selected_files, filter_name, output_file)
                    # Optionally do something with the original input files
                    self.handle_input_files_disposition(selected_files)
                    self.ui.message.setText("Combine completed")
                else:
                    # User cancelled from the file dialog
                    pass
            else:
                not_bias_error = QMessageBox()
                not_bias_error.setText("The selected files are not all Bias Frames")
                not_bias_error.setInformativeText("If you know the files are bias frames, they may not have proper FITS"
                                                   + " data internally. Check the \"Ignore FITS file type\" box"
                                                   + " to proceed anyway.")
                not_bias_error.setStandardButtons(QMessageBox.Ok)
                not_bias_error.setDefaultButton(QMessageBox.Ok)
                _ = not_bias_error.exec_()
        else:
            not_compatible = QMessageBox()
            not_compatible.setText("The selected files can't be combined.")
            not_compatible.setInformativeText("To be combined into a master file, the files must have identical"
                                              + " X and Y dimensions, and identical Binning values.")
            not_compatible.setStandardButtons(QMessageBox.Ok)
            not_compatible.setDefaultButton(QMessageBox.Ok)
            _ = not_compatible.exec_()

    # Get the file descriptors corresponding to the selected table rows
    def get_selected_file_descriptors(self) -> [FileDescriptor]:
        table_descriptors: [FileDescriptor] = self._table_model.get_file_descriptors()
        selected_rows: [int] = self.ui.filesTable.selectionModel().selectedRows()
        result: [FileDescriptor] = []
        for next_selected in selected_rows:
            row_index = next_selected.row()
            result.append(table_descriptors[row_index])
        return result

    # Prompt user for output file to receive combined file
    def get_output_file(self, suggested_file_path: str) -> str:
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        (file_name, _) = dialog.getSaveFileName(parent=None, caption="Master File", directory=suggested_file_path,
                                                filter="FITS files (*.FIT)")
        return None if len(file_name.strip()) == 0 else file_name

    # Combine the given files, output to the given output file
    # Use the combination algorithm given by the radio buttons on the main window
    def combine_files(self, input_files: [FileDescriptor], filter_name: str, output_path: str):
        substituted_file_name = SharedUtils.substitute_date_time_filter_in_string(output_path)
        file_names = [d.get_absolute_path() for d in input_files]
        # Get info about any precalibration that is to be done
        # If precalibration wanted, uses image file unless it's None, then use pedestal
        pre_calibrate: bool
        pedestal_value: int
        calibration_image: numpy.ndarray
        (pre_calibrate, pedestal_value, calibration_image) = (Constants.CALIBRATION_NONE, 0, None)
        method = self.get_combine_method()
        if method == Constants.COMBINE_MEAN:
            mean_data = RmFitsUtil.combine_mean(file_names, pre_calibrate, pedestal_value, calibration_image)
            if mean_data is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(substituted_file_name, mean_data,
                                                     mean_exposure, mean_temperature, filter_name,
                                                     "Master Bias MEAN combined")
        elif method == Constants.COMBINE_MEDIAN:
            median_data = RmFitsUtil.combine_median(file_names, pre_calibrate, pedestal_value, calibration_image)
            if median_data is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(substituted_file_name, median_data,
                                                     mean_exposure, mean_temperature, filter_name,
                                                     "Master Bias MEDIAN combined")
        elif method == Constants.COMBINE_MINMAX:
            number_dropped_points = int(self.ui.minMaxNumDropped.text())
            min_max_clipped_mean = RmFitsUtil.combine_min_max_clip(file_names, number_dropped_points,
                                                                   pre_calibrate, pedestal_value, calibration_image)
            if min_max_clipped_mean is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(substituted_file_name, min_max_clipped_mean,
                                                     mean_exposure, mean_temperature, filter_name,
                                                     f"Master Bias Min/Max Clipped "
                                                     f"(drop {number_dropped_points}) Mean combined")
        else:
            assert method == Constants.COMBINE_SIGMA_CLIP
            sigma_threshold = float(self.ui.sigmaThreshold.text())
            sigma_clipped_mean = RmFitsUtil.combine_sigma_clip(file_names, sigma_threshold,
                                                               pre_calibrate, pedestal_value, calibration_image)
            if sigma_clipped_mean is not None:
                (mean_exposure, mean_temperature) = RmFitsUtil.mean_exposure_and_temperature(file_names)
                RmFitsUtil.create_combined_fits_file(substituted_file_name, sigma_clipped_mean,
                                                     mean_exposure, mean_temperature, filter_name,
                                                     f"Master Bias Sigma Clipped "
                                                     f"(threshold {sigma_threshold}) Mean combined")

    # Determine which combination method is selected in the UI
    def get_combine_method(self) -> int:
        if self.ui.combineMeanRB.isChecked():
            return Constants.COMBINE_MEAN
        elif self.ui.combineMedianRB.isChecked():
            return Constants.COMBINE_MEDIAN
        elif self.ui.combineMinMaxRB.isChecked():
            return Constants.COMBINE_MINMAX
        else:
            assert self.ui.combineSigmaRB.isChecked()
            return Constants.COMBINE_SIGMA_CLIP

    # We're done combining files.  The user may want us to do something with the original input files
    def handle_input_files_disposition(self, descriptors: [FileDescriptor]):
        if self.ui.dispositionNothingRB.isChecked():
            # User doesn't want us to do anything with the input files
            pass
        else:
            assert (self.ui.dispositionSubFolderRB.isChecked())
            # User wants us to move the input files into a sub-folder
            SharedUtils.dispose_files_to_sub_folder(descriptors, self.ui.subFolderName.text())
            # Remove the files from the table since those paths are no longer valid
            self._table_model.remove_files(descriptors)

    # Determine if there are enough files selected for the Min-Max algorithm
    # If that algorithm isn't selected, then return True
    # Otherwise there should be more files selected than 2*n, where n is the
    # min-max clipping value
    def min_max_enough_files(self, num_selected: int) -> bool:
        if not self.ui.combineMinMaxRB.isChecked():
            return True
        else:
            return num_selected > (2 * int(self.ui.minMaxNumDropped.text()))
