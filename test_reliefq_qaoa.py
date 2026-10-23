from reliefq_qaoa import optimize_allocations

resources = [
    {
        "id": 1,
        "resource_name": "Water",
        "quantity": 100,
        "unit": "litres",
    },
    {
        "id": 2,
        "resource_name": "Food Packets",
        "quantity": 50,
        "unit": "packets",
    },
]

requests = [
    {
        "id": 101,
        "center_name": "Demo Relief Center A",
        "resource_name": "Water",
        "quantity": 60,
        "unit": "litres",
        "urgency": "Critical",
        "status": "Pending",
    },
    {
        "id": 102,
        "center_name": "Demo Relief Center B",
        "resource_name": "Food Packets",
        "quantity": 20,
        "unit": "packets",
        "urgency": "High",
        "status": "Pending",
    },
]

allocations = optimize_allocations(resources, requests)

print("\n=== ReliefQ QAOA Allocations ===")
for allocation in allocations:
    print(allocation)