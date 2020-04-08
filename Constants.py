class Constants:
    # Constants with weird arbitrary numeric values are being used to simulate "enum"s
    # The actual enum class isn't working well in my current version of Python.
    # The weird numbers are arbitrary, and are chosen to be weird to reduce the chance that
    # a "legitimate" number in some other variable is accidentally cross-assigned and mistaken.

    # What combination algorithm is used for combining multiple frames to a master?
    COMBINE_MEAN = -6172  # Simple mean of all frames
    COMBINE_MEDIAN = -6199  # Simple median of all frames
    COMBINE_MINMAX = -6233  # Remove min and max values then mean
    COMBINE_SIGMA_CLIP = -6345  # Remove values outside a given sigma then mean

    # What do we do with the raw input files after files are combined to a master flat?
    INPUT_DISPOSITION_NOTHING = -8357  # Do nothing to the files
    INPUT_DISPOSITION_SUBFOLDER = -8361  # Move to a given named subfolder


    @classmethod
    def combine_method_string(cls, method: int) -> str:
        if method == cls.COMBINE_MEAN:
            return "Mean"
        elif method == cls.COMBINE_MEDIAN:
            return "Median"
        elif method == cls.COMBINE_MINMAX:
            return "Min-Max Clip"
        else:
            assert method == cls.COMBINE_SIGMA_CLIP
            return "Sigma Clip"

    @classmethod
    def disposition_string(cls, value: int) -> str:
        if value == cls.INPUT_DISPOSITION_NOTHING:
            return "Nothing"
        else:
            assert value == cls.INPUT_DISPOSITION_SUBFOLDER
            return "SubFolder"

