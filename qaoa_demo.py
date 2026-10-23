from qiskit.primitives import StatevectorSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer


# ------------------------------------
# RELIEFQ: SAMPLE DISASTER DATA
# ------------------------------------

available_food_packets = 2

centers = [
    {"name": "Center A", "urgency": "Critical", "needed": 1, "priority": 10},
    {"name": "Center B", "urgency": "High", "needed": 1, "priority": 6},
    {"name": "Center C", "urgency": "Medium", "needed": 1, "priority": 2},
]


# ------------------------------------
# 1. CLASSICAL GREEDY ALGORITHM
# ------------------------------------

def greedy_allocation(centers, available):
    remaining = available
    allocations = {}

    # Give priority to the most urgent centers first.
    ordered = sorted(
        centers,
        key=lambda center: center["priority"],
        reverse=True,
    )

    for center in ordered:
        allocated = min(center["needed"], remaining)
        allocations[center["name"]] = allocated
        remaining -= allocated

    return allocations


# ------------------------------------
# 2. BUILD THE OPTIMIZATION PROBLEM
# ------------------------------------

problem = QuadraticProgram("ReliefQ_Food_Allocation")

# Each binary variable represents whether a center
# receives its one requested food packet.
for center in centers:
    problem.binary_var(name=center["name"])

# Maximize the priority-weighted food allocation.
problem.maximize(
    linear={
        center["name"]: center["priority"]
        for center in centers
    }
)

# Never allocate more packets than are available.
problem.linear_constraint(
    linear={
        center["name"]: 1
        for center in centers
    },
    sense="<=",
    rhs=available_food_packets,
    name="food_supply_limit",
)


# ------------------------------------
# 3. RUN QAOA ON A LOCAL SIMULATOR
# ------------------------------------

sampler = StatevectorSampler(
    default_shots=2048,
    seed=42,
)

qaoa = QAOA(
    sampler=sampler,
    optimizer=COBYLA(maxiter=100),
    reps=1,
)

optimizer = MinimumEigenOptimizer(qaoa)

print("\nRunning ReliefQ QAOA...")
qaoa_result = optimizer.solve(problem)


# ------------------------------------
# 4. RUN THE GREEDY BASELINE
# ------------------------------------

greedy_result = greedy_allocation(
    centers,
    available_food_packets,
)


# ------------------------------------
# 5. COMPARE RESULTS
# ------------------------------------

print("\n========== RELIEFQ RESULTS ==========")

print("\nCLASSICAL GREEDY ALGORITHM")
greedy_score = 0

for center in centers:
    amount = greedy_result[center["name"]]
    greedy_score += amount * center["priority"]

    print(
        f'{center["name"]}: {amount} packet(s) '
        f'| Urgency: {center["urgency"]}'
    )

print("Greedy priority score:", greedy_score)

print("\nQAOA ALGORITHM")
qaoa_score = 0

for index, center in enumerate(centers):
    amount = int(round(qaoa_result.x[index]))
    qaoa_score += amount * center["priority"]

    print(
        f'{center["name"]}: {amount} packet(s) '
        f'| Urgency: {center["urgency"]}'
    )

print("QAOA priority score:", qaoa_score)
print("QAOA objective value:", qaoa_result.fval)

print("\n=====================================")