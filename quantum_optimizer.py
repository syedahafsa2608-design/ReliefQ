from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import StatevectorSampler


def run_qaoa_demo():
    # Define a binary optimization problem.
    # Each variable is 1 if selected, or 0 if not selected.
    problem = QuadraticProgram("ReliefQ_QAOA")

    problem.binary_var("food")
    problem.binary_var("water")
    problem.binary_var("blankets")

    # Priority scores for the demo:
    # food = 3, water = 4, blankets = 5
    problem.maximize(
        linear={
            "food": 3,
            "water": 4,
            "blankets": 5,
        }
    )

    # Capacity: choose at most two supply units.
    problem.linear_constraint(
        linear={
            "food": 1,
            "water": 1,
            "blankets": 1,
        },
        sense="<=",
        rhs=2,
        name="supply_capacity",
    )

    # QAOA uses a quantum circuit and a classical
    # optimizer to search for a high-quality solution.
    sampler = StatevectorSampler(seed=42)

    qaoa = QAOA(
        sampler=sampler,
        optimizer=COBYLA(maxiter=100),
        reps=2,
    )

    solver = MinimumEigenOptimizer(qaoa)
    result = solver.solve(problem)

    print("\n=== ReliefQ: QAOA Result ===")
    print("Selected supplies:")

    for name, value in result.variables_dict.items():
        if value > 0.5:
            print(f"  - {name}")

    print(f"\nTotal priority score: {result.fval}")
    print(f"Solver status: {result.status}")


if __name__ == "__main__":
    run_qaoa_demo()