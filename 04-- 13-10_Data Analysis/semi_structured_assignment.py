import json
import pandas as pd

# 1. Load the JSON file using Python
with open("semi_structured_data.json", "r") as file:
    incidents = json.load(file)

print("\n=== All Incident Records Loaded ===")
print(incidents)

# 2. Print all incident IDs
print("\n=== Incident IDs ===")
for incident in incidents:
    print(incident["incident_id"])

# 3. Print the city of each incident
print("\n=== Cities ===")
for incident in incidents:
    print(incident["location"]["city"])

# 4. Display incidents where severity is High
print("\n=== High Severity Incidents ===")
for incident in incidents:
    if incident["severity"] == "High":
        print(incident)

# 5. Display incidents where category is Safety
print("\n=== Safety Category Incidents ===")
for incident in incidents:
    if incident["category"] == "Safety":
        print(incident)

# 6. Handle missing actions field
print("\n=== Actions Taken ===")
for incident in incidents:
    print(f"\nIncident: {incident['incident_id']}")

    if "actions" in incident:
        for action in incident["actions"]:
            print("-", action)
    else:
        print("No actions recorded")

# 7. Count incidents by severity level
print("\n=== Incident Count by Severity ===")

severity_count = {}

for incident in incidents:
    severity = incident["severity"]

    if severity in severity_count:
        severity_count[severity] += 1
    else:
        severity_count[severity] = 1

print(severity_count)

# 8. Add new field: status = Open
for incident in incidents:
    incident["status"] = "Open"

print("\n=== Status Added ===")
for incident in incidents:
    print(incident["incident_id"], "-", incident["status"])

# 9. Save updated records
with open("updated_incidents.json", "w") as file:
    json.dump(incidents, file, indent=4)

print("\nUpdated records saved to updated_incidents.json")

# 10. Convert JSON into Pandas DataFrame
df = pd.json_normalize(incidents)

print("\n=== DataFrame Output ===")
print(
    df[
        [
            "incident_id",
            "severity",
            "category",
            "location.city",
            "location.site"
        ]
    ]
)