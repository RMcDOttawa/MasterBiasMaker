import re
from typing import Optional


class Validators:
    # Validate floating point number such as latitude, longitude
    @classmethod
    def valid_float_in_range(cls, proposed_value: str,
                             min_value: float,
                             max_value: float) -> Optional[float]:
        """
        Validate that a string is a floating point number in a given range
        :param proposed_value:      String to be tested
        :param min_value:           Minimum acceptable value
        :param max_value:           Maximum acceptable value
        :return:                    Converted value if valid, None if not valid
        """

        result: Optional[float] = None
        try:
            converted: float = float(proposed_value)
            if (converted >= min_value) and (converted <= max_value):
                result = converted
        except ValueError:
            # Let result go back as "none", indicating error
            pass
        return result

    # Validate integer number

    @classmethod
    def valid_int_in_range(cls, proposed_value: str,
                           min_value: int,
                           max_value: int) -> Optional[int]:
        """
        Validate that a string is an integer in a given range
        :param proposed_value:      String to be tested
        :param min_value:           Minimum acceptable value
        :param max_value:           Maximum acceptable value
        :return:                    Converted value if valid, None if not valid
        """

        result: Optional[int] = None
        try:
            converted: int = int(proposed_value)
            if (converted >= min_value) and (converted <= max_value):
                result = converted
        except ValueError:
            # Let result go back as "none", indicating error
            pass
        return result

    @classmethod
    def valid_file_name(cls, proposed_name,
                        min_length,
                        max_length) -> bool:
        """
        Is the given string a valid file name (just the name, no extensions or slashes)?
        :param proposed_name:   Name to check
        :param min_length:      Minimum string length
        :param max_length:      Maximum string length
        :return:                Appears to be a valid file name?
        """
        assert 0 < min_length <= max_length
        result = False
        if min_length <= len(proposed_name) <= max_length:
            upper = proposed_name.upper()
            matched = re.fullmatch("[A-Z0-9_\\-$()]*", upper)
            result = bool(matched)
        return result
