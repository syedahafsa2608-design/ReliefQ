from time import perf_counter
import math

from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.converters import QuadraticProgramToQubo


PRIORITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

# Keep the simulator deliberately small for a local demo.
MAX_REQUESTS = 4
MAX_QUBITS = 12


def normalize(value):
    return str(value or "").strip().casefold()


def quantity_number(value):
    try:
        number = float(value or 0)
        if not math.isfinite(number):
            return 0.0
        return max(0.0, number)
    except (ValueError, TypeError):
        return 0.0


def _build_problem(candidates, supply):
    """Build a whole-request binary optimization model."""
    qp = QuadraticProgram("reliefq_qaoa")

    for i in range(len(candidates)):
        qp.binary_var(name=f"x_{i}")

    # Qiskit minimizes, so negate scores to maximize urgency/priority.
    max_quantity = max((row["quantity"] for row in candidates), default=1.0)
    weights = [
        PRIORITY.get(row["urgency"], 1)
        + 0.1 * row["quantity"] / max(max_quantity, 1.0)
        for row in candidates
    ]

    qp.minimize(
        linear={f"x_{i}": -weights[i] for i in range(len(candidates))}
    )

    # One supply constraint for each resource/unit represented.
    resource_keys = list(dict.fromkeys(row["key"] for row in candidates))

    for number, key in enumerate(resource_keys):
        coefficients = {
            f"x_{i}": row["quantity"]
            for i, row in enumerate(candidates)
            if row["key"] == key
        }
        qp.linear_constraint(
            linear=coefficients,
            sense="<=",
            rhs=supply.get(key, 0.0),
            name=f"supply_{number}",
        )

    return qp, weights


def _empty_result(started, message):
    return {
        "selected": [],
        "objective": 0.0,
        "runtime_seconds": perf_counter() - started,
        "message": message,
    }


def optimize_with_qaoa(resources, requests, max_requests=MAX_REQUESTS):
    """
    Small local QAOA prototype.

    Chooses whole requests subject to matching resource-supply constraints.
    It does not execute deliveries or modify inventory. If the full candidate
    set is too large for the demo's qubit limit, it progressively tries
    smaller candidate sets. A result is returned only when the converted
    QUBO fits within MAX_QUBITS.
    """
    started = perf_counter()

    # Aggregate supplies by normalized resource name and unit.
    supply = {}
    for item in resources:
        key = (
            normalize(item.get("resource_name")),
            normalize(item.get("unit", "units")),
        )
        if not key[0]:
            continue
        supply[key] = supply.get(key, 0.0) + quantity_number(
            item.get("quantity")
        )

    # Collect active requests that could be fulfilled in full.
    candidates = []
    for index, item in enumerate(requests):
        status = normalize(item.get("status", "pending"))
        if status in {"fulfilled", "completed", "cancelled"}:
            continue

        key = (
            normalize(item.get("resource_name")),
            normalize(item.get("unit", "units")),
        )
        quantity = quantity_number(item.get("quantity"))

        if not key[0] or quantity <= 0:
            continue
        if quantity > supply.get(key, 0.0):
            continue

        candidates.append({
            "index": index,
            "center": item.get("center_name", "Unknown center"),
            "resource": item.get("resource_name", ""),
            "unit": item.get("unit", "units"),
            "quantity": quantity,
            "urgency": normalize(item.get("urgency", "low")),
            "key": key,
        })

    candidates.sort(
        key=lambda row: (
            -PRIORITY.get(row["urgency"], 1),
            row["index"],
        )
    )

    if not candidates:
        return _empty_result(
            started,
            "No eligible whole requests fit within the available matching "
            "resource supply.",
        )

    # Try progressively smaller models. QUBO conversion may add slack
    # variables, so candidate count alone is not a reliable qubit estimate.
    requested_limit = max(1, int(max_requests))
    candidates = candidates[:requested_limit]
    converter = QuadraticProgramToQubo()
    qubo = None
    qp = None
    weights = None
    qubit_count = 0
    used_candidates = candidates

    while used_candidates:
        qp, weights = _build_problem(used_candidates, supply)
        try:
            qubo = converter.convert(qp)
            qubit_count = len(qubo.variables)
        except Exception as exc:
            return _empty_result(
                started,
                f"QAOA could not convert the optimization problem: {exc}",
            )

        print(
            "ReliefQ QAOA: "
            f"{len(used_candidates)} candidate requests -> "
            f"{qubit_count} qubits."
        )

        if qubit_count <= MAX_QUBITS:
            break

        used_candidates = used_candidates[:-1]

    if not used_candidates or qubo is None or qubit_count > MAX_QUBITS:
        return _empty_result(
            started,
            f"QAOA could not fit this problem within the {MAX_QUBITS}-qubit "
            "demo limit, even after reducing the candidate set. Use the "
            "Classical Greedy optimizer for this larger problem.",
        )

    # Solve only after confirming the converted model fits the safety limit.
    try:
        sampler = StatevectorSampler(default_shots=128, seed=42)
        qaoa = QAOA(
            sampler=sampler,
            optimizer=COBYLA(maxiter=8),
            reps=1,
        )
        solver = MinimumEigenOptimizer(
            qaoa,
            converters=[converter],
        )

        print("ReliefQ QAOA: starting solver.")
        result = solver.solve(qp)
        print("ReliefQ QAOA: solver completed.")

    except Exception as exc:
        return _empty_result(
            started,
            f"QAOA could not complete this run: {exc}. "
            "Try the Classical Greedy optimizer.",
        )

    selected = []
    for i, row in enumerate(used_candidates):
        if i < len(result.x) and result.x[i] > 0.5:
            selected.append({
                "Request Index": row["index"],
                "Relief Center": row["center"],
                "Resource": row["resource"],
                "Unit": row["unit"],
                "Urgency": row["urgency"].title(),
                "Requested Quantity": row["quantity"],
                "Priority Score": PRIORITY.get(row["urgency"], 1),
            })

    objective = sum(
        weights[i]
        for i in range(len(used_candidates))
        if i < len(result.x) and result.x[i] > 0.5
    )

    reduction_note = ""
    if len(used_candidates) < min(requested_limit, len(candidates)):
        reduction_note = (
            f" The candidate set was reduced to {len(used_candidates)} "
            "requests to fit the simulator limit."
        )

    return {
        "selected": selected,
        "objective": objective,
        "runtime_seconds": perf_counter() - started,
        "message": (
            f"QAOA finished using {qubit_count} qubits. "
            "This is a demo recommendation; verify real needs and supply "
            "before distribution."
            + reduction_note
        ),
    }