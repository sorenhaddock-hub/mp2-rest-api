import io
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src import (
    DatasetInfo,
    DatasetStorage,
    HealthResponse,
    ProcessConfig,
    ProcessingReport,
    log_requests,
    setup_logging,
)

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = DatasetStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".csv":
        logger.warning("Unsupported file format: %s", suffix or "(no extension)")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Please upload a .csv file.",
        )

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        logger.warning("Empty CSV upload: %s", file.filename)
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
    except pd.errors.ParserError as e:
        logger.warning("Could not parse CSV %s: %s", file.filename, e)
        raise HTTPException(status_code=400, detail=f"Could not parse CSV file: {e}")
    except UnicodeDecodeError:
        logger.warning("CSV is not valid UTF-8: %s", file.filename)
        raise HTTPException(
            status_code=400,
            detail="Could not decode the file. Make sure it is a UTF-8 encoded CSV.",
        )

    dataset_id = storage.save(df, file.filename)
    logger.info(
        "Uploaded dataset: id=%d, filename=%s, rows=%d",
        dataset_id, file.filename, len(df),
    )
    return storage.get_metadata(dataset_id)


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset not found: %d", dataset_id)
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info("Retrieved dataset: id=%d, returned_rows=%d", dataset_id, len(records))
    return {"id": dataset_id, "data": records, "total_rows": len(df)}


@app.post(
    "/datasets/{dataset_id}/process",
    response_model=ProcessingReport
)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # 1. Retrieve (outside the try block so a 404 stays a 404)
    df = storage.get(dataset_id)
    if df is None:
        logger.warning("Dataset not found: %d", dataset_id)
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    # 2. Convert request model to the dict structure MP1 expects
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]

    # 3. Every numeric column must exist
    missing_numeric = [col for col in numeric_columns if col not in df.columns]
    if missing_numeric:
        logger.warning(
            "Numeric columns not found in dataset %d: %s", dataset_id, missing_numeric
        )
        raise HTTPException(
            status_code=400,
            detail=f"Numeric columns not found in dataset: {missing_numeric}",
        )

    try:
        # 4. Validate
        rows_before_validation = len(df)
        validated = validate_dataframe(
            df,
            required_columns=required_columns,
            numeric_columns=numeric_columns,
        )
        # 5. Record rows removed, then copy before processing
        validation_rows_removed = rows_before_validation - len(validated)
        logger.info(
            "Validated dataset: id=%d, validation_removed=%d",
            dataset_id, validation_rows_removed,
        )
        validated_copy = validated.copy()

        # 6. Process with the full config
        processed = process_data(validated, config_dict)

        # 7. Cleaning report: validated copy vs processed
        cleaning_report = create_cleaning_report(validated_copy, processed)
    except ValueError as error:
        logger.warning("Processing failed for dataset %d: %s", dataset_id, error)
        raise HTTPException(status_code=400, detail=str(error))

    # 8. Only update storage after everything succeeded
    storage.update(dataset_id, processed)

    report = {key: int(value) for key, value in cleaning_report.items()}
    logger.info(
        "Processed dataset: id=%d, validation_removed=%d, rows_before=%d, rows_after=%d",
        dataset_id, validation_rows_removed,
        report.get("rows_before", len(validated_copy)),
        report.get("rows_after", len(processed)),
    )

    # 9. Return a dict matching ProcessingReport
    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": report,
    }