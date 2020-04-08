from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog

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

        # Set up responders for buttons and fields
        self.ui.combineMeanRB.clicked.connect(self.combine_mean_button_clicked)
        self.ui.combineMedianRB.clicked.connect(self.combine_median_button_clicked)
        self.ui.combineMinMaxRB.clicked.connect(self.combine_minmax_button_clicked)
        self.ui.combineSigmaRB.clicked.connect(self.combine_sigma_button_clicked)

        self.ui.dispositionNothingRB.clicked.connect(self.disposition_nothing_clicked)
        self.ui.dispositionSubFolderRB.clicked.connect(self.disposition_sub_folder_clicked)

        self.ui.closeButton.clicked.connect(self.close_button_clicked)

        # Input fields
        self.ui.minMaxNumDropped.editingFinished.connect(self.min_max_drop_changed)
        self.ui.sigmaThreshold.editingFinished.connect(self.sigma_threshold_changed)
        self.ui.subFolderName.editingFinished.connect(self.sub_folder_name_changed)

        self.enableFields()

    def combine_mean_button_clicked(self):
        """Combine Mean algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_MEAN)
        self.enableFields()

    def combine_median_button_clicked(self):
        """Combine Median algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_MEDIAN)
        self.enableFields()

    def combine_minmax_button_clicked(self):
        """Combine Min-Max algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_MINMAX)
        self.enableFields()

    def combine_sigma_button_clicked(self):
        """Combine Sigma-Clip algorithm button clicked. Record preference and enable/disable fields"""
        self._preferences.set_master_combine_method(Constants.COMBINE_SIGMA_CLIP)
        self.enableFields()

    def disposition_nothing_clicked(self):
        """Do nothing to input files radio button selected"""
        self._preferences.set_input_file_disposition(Constants.INPUT_DISPOSITION_NOTHING)
        self.enableFields()

    def disposition_sub_folder_clicked(self):
        """Move input files to sub-folder radio button selected"""
        self._preferences.set_input_file_disposition(Constants.INPUT_DISPOSITION_SUBFOLDER)
        self.enableFields()

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

    def enableFields(self):
        """Enable and disable window fields depending on button settings"""
        self.ui.minMaxNumDropped.setEnabled(self._preferences.get_master_combine_method() == Constants.COMBINE_MINMAX)
        self.ui.sigmaThreshold.setEnabled(self._preferences.get_master_combine_method() == Constants.COMBINE_SIGMA_CLIP)
        self.ui.subFolderName.setEnabled(
            self._preferences.get_input_file_disposition() == Constants.INPUT_DISPOSITION_SUBFOLDER)

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
