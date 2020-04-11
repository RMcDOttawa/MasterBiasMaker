from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant

from FileDescriptor import FileDescriptor


#   Model for the file table shown on the main UI.  The table consists of one row per file
#   identified in the "open" dialog, and the user will select the rows in the table that
#   are to be processed.

#   Columns in the table are:
#       0:  Name            Name of the file
#       1:  Type            Image type (Dark, Light, Bias, Flat, Unknown)
#       2:  Dimensions      Width, Height of image in pixels
#       3:  Binning         The binning value (1x1, 2x2, etc., or Unknown)
#       4:  Filter          Name of filter if light or flat frame
#       5:  Exposure        Exposure time of frame in seconds


class FitsFileTableModel(QAbstractTableModel):
    headings = ["Name", "Type", "Dimensions", "Binning", "Exp.", "Temp."]

    def __init__(self, ignore_file_type: bool):
        """Constructor for empty fits file table model"""
        QAbstractTableModel.__init__(self)
        self._files_list: [FileDescriptor] = []
        self._ignore_file_type = ignore_file_type

    def set_ignore_file_type(self, ignore: bool):
        self._ignore_file_type = ignore

    def get_file_descriptors(self):
        return self._files_list

    def set_file_descriptors(self, file_descriptors: [FileDescriptor]):
        self.beginResetModel()
        self._files_list = file_descriptors
        self.endResetModel()

    # Return how many rows (not including the header row) to display
    # noinspection PyMethodOverriding
    def rowCount(self, parent: QModelIndex) -> int:
        return len(self._files_list)

    # Return how many columns to display
    # noinspection PyMethodOverriding
    def columnCount(self, parent: QModelIndex) -> int:
        return len(self.headings)

    # Get data element to display in a table cell
    # noinspection PyMethodOverriding
    def data(self, index: QModelIndex, role: Qt.DisplayRole):
        row_index: int = index.row()
        column_index: int = index.column()
        if role == Qt.DisplayRole:
            descriptor = self._files_list[row_index]
            if column_index == 0:
                result = descriptor.get_name()
            elif column_index == 1:
                result = descriptor.get_type_name()
            elif column_index == 2:
                (x_size, y_size) = descriptor.get_dimensions()
                result = f"{x_size} x {y_size}"
            elif column_index == 3:
                binning = descriptor.get_binning()
                result = f"{binning} x {binning}"
            elif column_index == 4:
                result = f"{descriptor.get_exposure():.3f}"
            elif column_index == 5:
                result = str(descriptor.get_temperature())
            else:
                result = f"<{row_index},{column_index}>"
        # elif role == Qt.FontRole:
        # elif role == Qt.BackgroundRole:
        else:
            result = QVariant()
        return result

    # noinspection PyMethodOverriding
    def headerData(self, item_number, orientation, role):
        result = QVariant()
        if (role == Qt.DisplayRole) and (orientation == Qt.Horizontal):
            if 0 <= item_number < len(self.headings):
                return self.headings[item_number]
            else:
                return f"Head-{item_number}"
        # elif (role == Qt.DisplayRole) and (orientation == Qt.Vertical):
        # elif (role == Qt.FontRole) and (orientation == Qt.Vertical):
        # elif (role == Qt.FontRole) and (orientation == Qt.Horizontal):
        return result

    # Sort - called when one of the column headers is clicked for sorting

    # noinspection PyMethodOverriding
    def sort(self, column_index: int, sort_order: int):
        self.beginResetModel()
        reverse_flag = sort_order == 1
        if column_index == 0:
            self._files_list = sorted(self._files_list,
                                      key=FileDescriptor.get_name,
                                      reverse=reverse_flag)
        elif column_index == 1:
            self._files_list = sorted(self._files_list,
                                      key=FileDescriptor.get_type_name,
                                      reverse=reverse_flag)
        elif column_index == 2:
            self._files_list = sorted(self._files_list,
                                      key=FileDescriptor.get_x_dimension,
                                      reverse=reverse_flag)
        elif column_index == 3:
            self._files_list = sorted(self._files_list,
                                      key=FileDescriptor.get_binning,
                                      reverse=reverse_flag)
        elif column_index == 4:
            self._files_list = sorted(self._files_list,
                                      key=FileDescriptor.get_exposure,
                                      reverse=reverse_flag)
        elif column_index == 5:
            self._files_list = sorted(self._files_list,
                                      key=FileDescriptor.get_temperature,
                                      reverse=reverse_flag)
        self.endResetModel()

    # We only allow the selection of files that are known to be FLAT frames.
    # Or, if the "ignore file type" flag is on, then we allow the selection of any files
    def flags(self, index: QModelIndex):
        selectable_option: int
        if self._ignore_file_type:
            # We're ignoring internal FITS file type, so all rows are selectable
            selectable_option = Qt.ItemIsSelectable
        else:
            # We're honouring FITS file type, so we allow selection only of FLAT files
            row_index = index.row()
            descriptor = self._files_list[row_index]
            selectable_option = Qt.ItemIsSelectable if descriptor.get_type() == FileDescriptor.FILE_TYPE_BIAS else 0
        return selectable_option | Qt.ItemIsEnabled

    # Clear all the data from the table
    def clear_table(self):
        self.beginResetModel()
        self._files_list = []
        self.endResetModel()

    # Remove the given files from the table (probably because we have moved them
    # so the file path is no longer valid)

    def remove_files(self, descriptors):
        descriptor: FileDescriptor
        for descriptor in descriptors:
            name_to_remove = descriptor.get_name()
            # Find occurrence of this (there is only one) and remove that row
            for row_index in range(len(self._files_list)):
                if self._files_list[row_index].get_name() == name_to_remove:
                    model_index = self.createIndex(row_index, 0)
                    self.beginRemoveRows(model_index.parent(), row_index, row_index)
                    del self._files_list[row_index]
                    self.endRemoveRows()
                    break
