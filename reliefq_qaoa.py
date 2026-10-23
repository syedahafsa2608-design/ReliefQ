from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import (
    QuadraticProgramToQubo,
)
from qiskit_optimization.algorithms import (
    MinimumEigenOptimizer,
)
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import StatevectorSampler


URGENCY_SCORE = {
    "critical": 100,
    "high": 50,
    "medium": 20,
    "low": 10,
}


def optimize_allocations(resources, requests, max_candidates=12):
    """
    resources and requests are lists of dictionaries.

    Resources require:
      id, resource_name, quantity, unit

    Requests require:
      id, resource_name, quantity, unit, urgency

    Returns a list of proposed allocations.
    """

    candidates = []

    for req in requests:
        if str(req.get("status", "Pending")).lower() not in (
            "pending", "approved"
        ):
            continue

        for supply in resources:
            same_name = (
                str(supply.get("resource_name", "")).strip().lower()
                == str(req.get("resource_name", "")).strip().lower()
            )
            same_unit = (
                str(supply.get("unit", "")).strip().lower()
                == str(req.get("unit", "")).strip().lower()
            )

            if same_name and same_unit:
                candidates.append({
                    "request_id": req["id"],
                    "center": req.get("center_name", "Relief center"),
                    "resource": supply["resource_name"],
                    "unit": supply["unit"],
                    "supply_id": supply["id"],
                    "urgency": str(req.get("urgency", "low")).lower(),
                    "priority": URGENCY_SCORE.get(
                        str(req.get("urgency", "low")).lower(), 10
                    ),
                    "available": max(0, int(supply.get("quantity", 0))),
                    "needed": max(0, int(req.get("quantity", 0))),
                })

    # Keep the simulator problem small for the first version.
    candidates = candidates[:max_candidates]

    if not candidates:
        return []

    # Each binary variable represents one possible supply/request match.
    problem = QuadraticProgram("ReliefQ_Allocation")

    for i in range(len(candidates)):
        problem.binary_var(name=f"x{i}")

    # Reward allocating supplies to urgent requests.
    # Quantity is capped at the smaller of available and requested.
    rewards = {}
    for i, item in enumerate(candidates):
        amount = min(item["available"], item["needed"])
        rewards[f"x{i}"] = item["priority"] * amount

    problem.maximize(linear=rewards)

    # Convert the constrained optimization problem to a QUBO.
    # The capacity constraints are expressed below as penalties
    # in the objective using pairs of conflicting assignments.
    #
    # A simple binary candidate model treats each candidate as
    # one allocation decision, so this first version is best for
    # small demonstration datasets with limited candidate counts.

    # Prevent allocating more than the supply's available quantity
    # or the request's needed quantity by selecting no more than
    # one candidate per request or supply.
    quadratic = {}

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            a = candidates[i]
            b = candidates[j]

            conflict = (
                a["supply_id"] == b["supply_id"]
                or a["request_id"] == b["request_id"]
            )

            if conflict:
                quadratic[(f"x{i}", f"x{j}")] = -100000

    # Qiskit accepts quadratic objective terms as a dictionary.
    # Add the conflict penalties to the maximization objective.
    problem.maximize(
        linear=rewards,
        quadratic=quadratic,
    )

    sampler = StatevectorSampler(seed=42)
    qaoa = QAOA(
        sampler=sampler,
        optimizer=COBYLA(maxiter=100),
        reps=2,
    )

    solver = MinimumEigenOptimizer(qaoa)
    result = solver.solve(problem)

    allocations = []

    for i, item in enumerate(candidates):
        if result.variables_dict.get(f"x{i}", 0) > 0.5:
            allocations.append({
                "center": item["center"],
                "request_id": item["request_id"],
                "resource": item["resource"],
                "quantity": min(
                    item["available"], item["needed"]
                ),
                "unit": item["unit"],
                "urgency": item["urgency"].title(),
                "supply_id": item["supply_id"],
            })

    return allocations