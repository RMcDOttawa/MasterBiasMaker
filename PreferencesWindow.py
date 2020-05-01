from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

from Constants import Constants
from MultiOsUtil import MultiOsUtil
from Preferences import Preferences
from SharedUtils import SharedUtils
from Validators import Validators


class PreferencesWindow(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = uic.loadUi(MultiOsUtil.path_for_file_in_program_directory("PreferencesWindow.ui"))
        self._preferences: Preferences

    def set_up_ui(self, preferences: Preferences):
        """Set UI fields in the dialog from the given preferences settings"""
        self._preferences = preferences

        # Fill in the UI fields from the preferences object

        # Disable algorithm text fields, then re-enable with the corresponding radio button
        self.ui.minMaxNumDropped.setEnabled(False)
        self.ui.sigmaThreshold.setEnabled(False)

        # Combination algorithm radio buttons
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

        # Disposition of input files
        disposition = preferences.get_input_file_disposition()
        if disposition == Constants.INPUT_DISPOSITION_SUBFOLDER:
            self.ui.dispositionSubFolderRB.setChecked(True)
        else:
            assert (disposition == Constants.INPUT_DISPOSITION_NOTHING)
            self.ui.dispositionNothingRB.setChecked(True)
        self.ui.subFolderName.setText(preferences.get_disposition_subfolder_name())

        # Grouping information
        self.ui.groupBySizeCB.setChecked(preferences.get_group_by_size())
        self.ui.groupByTemperatureCB.setChecked(preferences.get_group_by_temperature())
        self.ui.ignoreSmallGroupsCB.setChecked(preferences.get_ignore_groups_fewer_than())

        self.ui.temperatureGroupTolerance.setText(f"{100 * preferences.get_temperature_group_tolerance():.0f}")
        self.ui.minimumGroupSize.setText(str(preferences.get_minimum_group_size()))

        # Set up responders for buttons and fields
        self.ui.combineMeanRB.clicked.connect(self.combine_mean_button_clicked)
        self.ui.combineMedianRB.clicked.connect(self.combine_median_button_clicked)
        self.ui.combineMinMaxRB.clicked.connect(self.combine_minmax_button_clicked)
        self.ui.combineSigmaRB.clicked.connect(self.combine_sigma_button_clicked)

        self.ui.dispositionNothingRB.clicked.connect(self.disposition_nothing_clicked)
        self.ui.dispositionSubFolderRB.clicked.connect(self.disposition_sub_folder_clicked)

        self.ui.groupBySizeCB.clicked.connect(self.group_by_size_clicked)
        self.ui.groupByTemperatureCB.clicked.connect(self.group_by_temperature_clicked)
        self.ui.ignoreSmallGroupsCB.clicked.connect(self.ignore_small_groups_clicked)

        self.ui.closeButton.clicked.connect(self.close_button_clicked)

        # Input fields
        self.ui.minMaxNumDropped.editingFinished.connect(self.min_max_drop_changed)
        self.ui.sigmaThreshold.editingFinished.connect(self.sigma_threshold_changed)
        self.ui.subFolderName.editingFinished.connect(self.sub_folder_name_changed)
        self.ui.temperatureGroupTolerance.editingFinished.connect(self.temperature_group_tolerance_changed)
        self.ui.minimumGroupSize.editingFinished.connect(self.minimum_group_size_changed)

        self.enable_fields()

    def group_by_size_clicked(self):
        self._preferences.set_group_by_size(self.ui.groupBySizeCB.isChecked())
        self.enable_fields()

    def group_by_temperature_clicked(self):
        self._preferences.set_group_by_temperature(self.ui.groupByTemperatureCB.isChecked())
        self.enable_fields()

    def ignore_small_groups_clicked(self):
        self._preferences.set_ignore_groups_fewer_than(self.ui.ignoreSmallGroupsCB.isChecked())
        self.enable_fields()

    def combine_mean_button_clicked(self):
        """Combine Mean algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_MEAN)
        self.enable_fields()

    def combine_median_button_clicked(self):
        """Combine Median algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_MEDIAN)
        self.enable_fields()

    def combine_minmax_button_clicked(self):
        """Combine Min-Max algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_MINMAX)
        self.enable_fields()

    def combine_sigma_button_clicked(self):
        """Combine Sigma-Clip algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_SIGMA_CLIP)
        self.enable_fields()

    def disposition_nothing_clicked(self):
        """Do nothing to input files radio button selected"""
        self._preferences.set_input_file_disposition(Constants.INPUT_DISPOSITION_NOTHING)
        self.enable_fields()

    def disposition_sub_folder_clicked(self):
        """Move input files to sub-folder radio button selected"""
        self._preferences.set_input_file_disposition(Constants.INPUT_DISPOSITION_SUBFOLDER)
        self.enable_fields()

    def temperature_group_tolerance_changed(self):
        """User has entered value in temperature group tolerance field.  Validate and save"""
        proposed_new_number: str = self.ui.temperatureGroupTolerance.text()
        new_number = Validators.valid_float_in_range(proposed_new_number, 0.0, 99.999)
        valid = new_number is not None
        if valid:
            self._preferences.set_temperature_group_tolerance(new_number / 100.0)
        SharedUtils.background_validity_color(self.ui.temperatureGroupTolerance, valid)

    def minimum_group_size_changed(self):
        """User has entered value in minimum group size field.  Validate and save"""
        proposed_new_number: str = self.ui.minimumGroupSize.text()
        new_number = Validators.valid_int_in_range(proposed_new_number, 1, 32767)
        valid = new_number is not None
        if valid:
            self._preferences.set_minimum_group_size(new_number)
        SharedUtils.background_validity_color(self.ui.minimumGroupSize, valid)

    def min_max_drop_changed(self):
        """the field giving the number of minimum and maximum values to drop has been changed.
        Validate it (integer > 0) and store if valid"""
        proposed_new_number: str = self.ui.minMaxNumDropped.text()
        new_number = Validators.valid_int_in_range(proposed_new_number, 0, 256)
        valid = new_number is not None
        if valid:
            self._preferences.set_min_max_number_clipped_per_end(new_number)
        SharedUtils.background_validity_color(self.ui.minMaxNumDropped, valid)

    def sigma_threshold_changed(self):
        """the field giving the sigma limit beyond which values are ignored has changed
        Validate it (floating point > 0) and store if valid"""
        proposed_new_number: str = self.ui.sigmaThreshold.text()
        new_number = Validators.valid_float_in_range(proposed_new_number, 0.01, 100.0)
        valid = new_number is not None
        if valid:
            self._preferences.set_sigma_clip_threshold(new_number)
        SharedUtils.background_validity_color(self.ui.sigmaThreshold, valid)

    def sub_folder_name_changed(self):
        """the field giving the name of the sub-folder to be created or used has changed.
        Validate that it is an acceptable folder name and store if valid"""
        proposed_new_name: str = self.ui.subFolderName.text()
        # valid = Validators.valid_file_name(proposed_new_name, 1, 31)
        valid = SharedUtils.validate_folder_name(proposed_new_name)
        if valid:
            self._preferences.set_disposition_subfolder_name(proposed_new_name)
        SharedUtils.background_validity_color(self.ui.subFolderName, valid)

    def enable_fields(self):
        """Enable and disable window fields depending on button settings"""
        self.ui.minMaxNumDropped.setEnabled(self._preferences.get_master_combine_method() == Constants.COMBINE_MINMAX)
        self.ui.sigmaThreshold.setEnabled(self._preferences.get_master_combine_method() == Constants.COMBINE_SIGMA_CLIP)
        self.ui.subFolderName.setEnabled(
            self._preferences.get_input_file_disposition() == Constants.INPUT_DISPOSITION_SUBFOLDER)
        self.ui.temperatureGroupTolerance.setEnabled(self._preferences.get_group_by_temperature())
        self.ui.minimumGroupSize.setEnabled(self._preferences.get_ignore_groups_fewer_than())

    def close_button_clicked(self):
        """Close button has been clicked - close the preferences window"""
        # Lock-in any edits in progress in the text fields
        if self.ui.combineMinMaxRB.isChecked():
            self.min_max_drop_changed()
        if self.ui.combineSigmaRB.isChecked():
            self.sigma_threshold_changed()
        if self.ui.dispositionSubFolderRB.isChecked():
            self.sub_folder_name_changed()

        self.ui.close()
