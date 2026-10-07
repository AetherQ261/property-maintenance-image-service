from property_service import MaintenanceRequest, prioritize


def test_maintenance_priority_uses_issue_and_due_date():
    assert prioritize(MaintenanceRequest("T", "B", "x.jpg", "leak under sink", 7)) == "urgent"
    assert prioritize(MaintenanceRequest("T", "B", "x.jpg", "paint scuff", 2)) == "soon"
    assert prioritize(MaintenanceRequest("T", "B", "x.jpg", "paint scuff", 10)) == "scheduled"
