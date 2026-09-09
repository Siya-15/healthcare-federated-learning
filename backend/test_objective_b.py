from app.services.objective_b_service import build_objective_b_response

print("SERVICE IMPORTED")

try:
    result = build_objective_b_response(
        refresh=False,
        include_records=False,
        record_limit=100,
    )

    print("SUCCESS")
    print(result)

except Exception as e:
    import traceback
    traceback.print_exc()