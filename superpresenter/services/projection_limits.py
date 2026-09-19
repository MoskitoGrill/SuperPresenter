"""Shared capacities for stationary worship projection only."""
DEFAULT_HALL_ROWS = 8
STREAM_STANDARD_ROWS = 4


def row_limits(hall_rows=DEFAULT_HALL_ROWS):
    if type(hall_rows) is not int or hall_rows < 1:
        raise ValueError('Počet řádků musí být kladné celé číslo.')
    return hall_rows, min(STREAM_STANDARD_ROWS, hall_rows)
