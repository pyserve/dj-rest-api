import io

import pandas as pd
from celery import shared_task
from django.apps import apps
from django.core.files.base import ContentFile

from core.models import Import


@shared_task(bind=True)
def start_import(self, app_label, model_name, id, required_fields):
    Model = apps.get_model(app_label, model_name)
    record = Import.objects.get(pk=id)
    df = pd.read_csv(record.file.path, dtype=str, low_memory=False)
    df = df.dropna(how="all").replace(r"^\s*$", None, regex=True).dropna(how="all")
    rows = df.to_dict(orient="records")
    action = record.action
    mappings = record.mappings

    results = []
    if action == "create":
        total = len(rows)
        for idx, row in enumerate(rows, start=1):
            self.update_state(state="PENDING", meta={"current": idx, "total": total})
            missing = [
                field
                for field in required_fields
                if pd.isna(row.get(mappings[field]))
                or str(row.get(mappings[field])).strip() == ""
            ]
            if missing:
                results.append(
                    {
                        "row": idx,
                        "status": "error",
                        "message": f"Missing required fields: {', '.join(missing)}",
                    }
                )
                continue
            try:
                values = {field: row[col] for field, col in mappings.items()}
                obj = Model.objects.create(**values)
                results.append({"row": idx, "status": "success", "message": obj.id})
            except Exception as e:
                results.append({"row": idx, "status": "error", "message": str(e)})
    results_df = pd.DataFrame(results)
    print(results_df)
    buffer = io.StringIO()
    results_df.to_csv(buffer, index=False)
    buffer.seek(0)
    record.results.save(f"results_{record.id}.csv", ContentFile(buffer.getvalue()))
    record.save()
