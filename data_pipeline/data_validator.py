"""
Data Validator Module
DS 3500 - MP1 Part 4
"""
import logging
import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """
    # Every required column must be present
    for col in required_columns:
        if col not in df.columns:
            logger.error("Required column missing: %s", col)
            raise ValueError(f"Required column missing: {col}")

    df = df.copy()
    rows_before = len(df)

    for col in numeric_columns:
        if col not in df.columns:
            logger.error("Numeric column missing: %s", col)
            raise ValueError(f"Numeric column missing: {col}")

        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    invalid_rows.append(i)

        # Remove the invalid rows
        if invalid_rows:
            logger.warning(
                "Removed %d rows with invalid numeric values in %s",
                len(invalid_rows), col,
            )
            df = df.drop(index=invalid_rows)

        # Convert to a numeric data type
        df[col] = pd.to_numeric(df[col])

    logger.debug(
        "Validation: %d -> %d rows (%d removed)",
        rows_before, len(df), rows_before - len(df),
    )
    return df
