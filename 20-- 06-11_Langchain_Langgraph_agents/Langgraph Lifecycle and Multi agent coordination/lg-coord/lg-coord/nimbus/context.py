"""Who is using the agent. Passed at run time, never typed by the model."""
from dataclasses import dataclass


@dataclass
class Employee:
    employee_id: str
    office: str              # "india" or "germany"
    role: str = "employee"   # "employee", "manager" or "hr"
