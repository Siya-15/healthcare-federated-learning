from fastapi import APIRouter

from .. import data

router = APIRouter()


@router.get("/hospitals")
def list_hospitals():
    hm = data.hospital_master()
    df = data.encounters()
    counts = df["hospital_id"].value_counts().to_dict()

    out = []
    for _, r in hm.iterrows():
        hid = r["hospital_id"]
        item = {"hospital_id": hid, "encounter_count": int(counts.get(hid, 0))}
        for col in hm.columns:
            if col != "hospital_id":
                item[col] = None if str(r[col]) == "nan" else str(r[col])
        out.append(item)

    return {"count": len(out), "hospitals": out}
