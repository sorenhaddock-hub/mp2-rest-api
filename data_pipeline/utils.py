"""
Utility functions shared by the pipeline.
DS 3500 - MP1 Part 4
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(verbose=False):
    """Configure logging for the pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def validate_input(filepath):
    """Check whether the input path exists and is a file."""
    path = Path(filepath)
    if not path.exists():
        logger.error("Input file not found: %s", filepath)
        return False
    if not path.is_file():
        logger.error("Input path is not a file: %s", filepath)
        return False
    logger.info("Input file validated: %s", filepath)
    return True
