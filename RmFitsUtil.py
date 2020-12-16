from astropy.io import fits
from numpy.core.multiarray import ndarray

from FileDescriptor import FileDescriptor


class RmFitsUtil:

    # Take a best guess at what kind of file this is.  Use FITS header if present, but if that
    # is not present, then guess from file name, looking for keywords such as Dark, Bias, Flat,
    # Lum, Light, or a common filter name.  Optional array of light keywords can be given.
    # Result is an integer matching TheSkyX ccdsoftImageFrame type
    #   0 = Unknown
    #   1 = Light
    #   2 = Bias
    #   3 = Dark
    #   4 = Flat

    # (type_code, bin_x, bin_y, filter) = RmFitsUtil.categorize_file(name)
    @classmethod
    def make_file_descriptor(cls, absolute_path):
        """
        Create a file descriptor describing important attributes of file at given path
        :param absolute_path:   Path to file
        :return:                Descriptor of file
        """
        descriptor = FileDescriptor(absolute_path)

        (type_code, x_size, y_size, x_bin, y_bin, filter_name, exposure, temperature) \
            = cls.categorize_file(absolute_path)
        descriptor.set_type(type_code)
        descriptor.set_binning(x_bin, y_bin)
        descriptor.set_dimensions(x_size, y_size)
        descriptor.set_filter_name(filter_name)
        descriptor.set_exposure(exposure)
        descriptor.set_temperature(temperature)

        return descriptor

    @classmethod
    def categorize_file(cls,
                        file_name: str,
                        light_keywords: [str] = ("light", "lum", "red", "green", "blue", "ha")) \
            -> (int, int, int, int, int, str, float, float):
        """Determine what kind of FITS file the given name is - dark, light, bias, or flat.
        If no FITS keyword exists with this information, try to guess by looking for telltale
        words in the file name itself.  Return:
            integer type code
            x dimension
            y dimension
            x binning
            y binning
            filter name
            exposure time in seconds
            temperature of CCD"""
        x_size = 0
        y_size = 0
        exposure = 0.0
        temperature = 0.0
        with fits.open(file_name) as file:
            primary = file[0]
            header = primary.header
            # Image type
            if 'PICTTYPE' in header:
                # This keyword codes the file type directly
                result = int(header['PICTTYPE'])
            elif 'IMAGETYP' in header:
                type_code = header['IMAGETYP'].upper()
                if 'BIAS' in type_code:
                    result = FileDescriptor.FILE_TYPE_BIAS
                elif 'DARK' in type_code:
                    result = FileDescriptor.FILE_TYPE_DARK
                elif 'FLAT' in type_code:
                    result = FileDescriptor.FILE_TYPE_FLAT
                elif 'LIGHT' in type_code:
                    result = FileDescriptor.FILE_TYPE_LIGHT
                else:
                    result = FileDescriptor.FILE_TYPE_UNKNOWN
            else:
                fn_upper = file_name.upper()
                if 'BIAS' in fn_upper:
                    result = FileDescriptor.FILE_TYPE_BIAS
                elif 'DARK' in fn_upper:
                    result = FileDescriptor.FILE_TYPE_DARK
                elif 'FLAT' in fn_upper:
                    result = FileDescriptor.FILE_TYPE_FLAT
                else:
                    result = FileDescriptor.FILE_TYPE_UNKNOWN
                    for keyword in light_keywords:
                        if keyword.upper() in fn_upper:
                            result = FileDescriptor.FILE_TYPE_LIGHT
            # Binning values
            x_binning, y_binning, filter_name = 0, 0, ""
            if "XBINNING" in header:
                x_binning = header["XBINNING"]
            if "YBINNING" in header:
                y_binning = header["YBINNING"]
            # Filter name
            if "FILTER" in header:
                filter_name = header["FILTER"]
            # Dimensions
            if "NAXIS" in header:
                number_axes = header["NAXIS"]
                assert number_axes == 2
                x_size = header["NAXIS1"]
                y_size = header["NAXIS2"]
            # Exposure
            if "EXPOSURE" in header:
                exposure = header["EXPOSURE"]
            elif "EXPTIME" in header:
                exposure = header["EXPTIME"]
            # Temperature
            if "CCD-TEMP" in header:
                temperature = header["CCD-TEMP"]
            return result, x_size, y_size, x_binning, y_binning, filter_name, exposure, temperature

    @classmethod
    def create_combined_fits_file(cls, name: str,
                                  data: ndarray,
                                  file_type_code: int,
                                  image_type_string: str,
                                  exposure: float,
                                  temperature: float,
                                  filter_name: str,
                                  binning: int,
                                  comment: str):
        """Write a new FITS file with the given data and name.
        Create a FITS header in the file by copying the header from a given existing file
        and adding a given comment"""

        #  Create header
        header = fits.Header()
        header["FILTER"] = filter_name
        header["COMMENT"] = comment
        header["EXPTIME"] = exposure
        header["CCD-TEMP"] = temperature
        header["SET-TEMP"] = temperature
        header["XBINNING"] = binning
        header["YBINNING"] = binning
        header["PICTTYPE"] = file_type_code
        header["IMAGETYP"] = image_type_string

        # Create primary HDU
        data_16_bit = data.round().astype("i2")
        primary_hdu = fits.PrimaryHDU(data_16_bit, header=header)

        # Create HDUL
        hdul = fits.HDUList([primary_hdu])

        # Write to file
        hdul.writeto(name, output_verify="fix", overwrite=True, checksum=True)

    @classmethod
    def fits_file_type_string(cls, file_type):
        """
        Translate fits file type code number to string for file name
        :param file_type:   File type numeric code
        :return:            String for file name
        """
        if file_type == FileDescriptor.FILE_TYPE_BIAS:
            return "BIAS"
        elif file_type == FileDescriptor.FILE_TYPE_DARK:
            return "DARK"
        elif file_type == FileDescriptor.FILE_TYPE_FLAT:
            return "FLAT"
        elif file_type == FileDescriptor.FILE_TYPE_LIGHT:
            return "LIGHT"
        else:
            return "UNKNOWN"

    @classmethod
    def read_all_files_data(cls, file_names: [str]) -> [ndarray]:
        """
        Read ndarray data arrays for all the given file names.
        :param file_names:  List of file names
        :return:            List of 2-dimensional matrices of pixel values
        """
        result_array: [ndarray] = []
        for name in file_names:
            result_array.append(cls.fits_data_from_path(name))
        return result_array

    @classmethod
    def fits_data_from_path(cls, file_name: str) -> ndarray:
        """
        Get the image data from a fits file for one file, given the file path
        :param file_name:   Path to fits file to be read
        :return:            Matrix of pixel values representing the image
        """
        with fits.open(file_name) as hdul:
            primary = hdul[0]
            # Exposure and temperature
            return primary.data.astype(float)

    @classmethod
    def make_file_descriptions(cls, file_names: [str]) -> [FileDescriptor]:
        """
        Make a list of file descriptors for the files in the given list of names
        :param file_names:  List of names to be described
        :return:            List of descriptors
        """
        result: [FileDescriptor] = []
        for absolute_path in file_names:
            descriptor = RmFitsUtil.make_file_descriptor(absolute_path)
            result.append(descriptor)
        return result

