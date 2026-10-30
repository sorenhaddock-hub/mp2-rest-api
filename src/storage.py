import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    def save(self, df, filename):
        self._counter += 1
        dataset_id = self._counter
        self._store[dataset_id] = {"filename": filename, "df": df.copy()}
        logger.debug("Stored dataset: id=%d, rows=%d", dataset_id, len(df))
        return dataset_id
        pass

    def get(self, dataset_id):
        entry = self._store.get(dataset_id)
        if entry is None:
            return None
        df = entry["df"].copy()
        logger.debug("Retrieved dataset copy: id=%d, rows=%d", dataset_id, len(df))
        return df
        pass

    def get_metadata(self, dataset_id):
        entry = self._store.get(dataset_id)
        if entry is None:
            return None
        df = entry["df"]
        return {
            "id": dataset_id,
            "filename": entry["filename"],
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": [str(c) for c in df.columns],
        }
        pass

    def update(self, dataset_id, df):
        if dataset_id not in self._store:
            return False
        self._store[dataset_id]["df"] = df.copy()
        logger.debug("Updated dataset: id=%d, rows=%d", dataset_id, len(df))
        return True
        pass