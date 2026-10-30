"""
Configuration for WorkforceIQ Synthetic Workforce Data Generator.
Defines parameters, seeds, date ranges, salary bands, and distributions.
"""

from datetime import date
from typing import Dict, Any
import uuid
import random

def generate_deterministic_uuid() -> str:
    """Generates a UUID version 4 seeded by random state for 100% bit-for-bit reproducibility."""
    return str(uuid.UUID(int=random.getrandbits(128), version=4))

# Primary deterministic random seed as required by challenge
RANDOM_SEED: int = 20261022

# Simulation Observation Window: 24 Months
SIMULATION_START_DATE: date = date(2024, 11, 1)
SIMULATION_END_DATE: date = date(2026, 10, 31)
HISTORICAL_LOOKBACK_YEARS: int = 6  # Historical hires allowed back to 2018

# Cohort Sizes
STARTER_EMPLOYEE_COUNT: int = 150
FULL_EMPLOYEE_COUNT: int = 10000

# Target Attrition Boundaries (5% - 15% voluntary attrition over 24 months)
MIN_VOLUNTARY_ATTRITION_RATE: float = 0.05
MAX_VOLUNTARY_ATTRITION_RATE: float = 0.15
TARGET_VOLUNTARY_ATTRITION_RATE: float = 0.098  # Realistic ~9.8% annualized/period rate
INVOLUNTARY_ATTRITION_RATE: float = 0.015       # ~1.5% performance/layoff terminations
RETIREMENT_ATTRITION_RATE: float = 0.007        # ~0.7% normal retirements

# Anomaly Injection Quotas (for full 10k dataset)
ANOMALY_QUOTAS: Dict[str, int] = {
    "POST_TERMINATION_ACTIVITY": 45,      # ANOM-01
    "CIRCULAR_HIERARCHY": 12,             # ANOM-02 (reporting cycles & orphan nodes)
    "COMPENSATION_INVERSION": 50,         # ANOM-03 (salary out of band & inversions)
    "LEAVE_HOUR_CONFLICT": 40,            # ANOM-04 (billable work during approved leave)
}

# Engagement Survey Missingness Rate (~8% missing pulse response)
SURVEY_MISSINGNESS_RATE: float = 0.08

# Standard Enterprise Grade Levels & Salary Bands (USD)
GRADE_SALARY_BANDS: Dict[int, Dict[str, float]] = {
    1: {"min": 45000.0, "mid": 55000.0, "max": 65000.0, "title_prefix": "Associate"},
    2: {"min": 55000.0, "mid": 68000.0, "max": 80000.0, "title_prefix": "Junior"},
    3: {"min": 70000.0, "mid": 85000.0, "max": 100000.0, "title_prefix": "Mid-Level"},
    4: {"min": 85000.0, "mid": 105000.0, "max": 125000.0, "title_prefix": "Senior I"},
    5: {"min": 105000.0, "mid": 130000.0, "max": 155000.0, "title_prefix": "Senior II"},
    6: {"min": 125000.0, "mid": 155000.0, "max": 185000.0, "title_prefix": "Lead / Staff"},
    7: {"min": 145000.0, "mid": 180000.0, "max": 215000.0, "title_prefix": "Senior Staff"},
    8: {"min": 170000.0, "mid": 210000.0, "max": 255000.0, "title_prefix": "Principal"},
    9: {"min": 195000.0, "mid": 245000.0, "max": 295000.0, "title_prefix": "Senior Principal"},
    10: {"min": 225000.0, "mid": 285000.0, "max": 345000.0, "title_prefix": "Manager / Specialist Lead"},
    11: {"min": 260000.0, "mid": 330000.0, "max": 400000.0, "title_prefix": "Senior Manager"},
    12: {"min": 300000.0, "mid": 380000.0, "max": 465000.0, "title_prefix": "Director"},
    13: {"min": 350000.0, "mid": 450000.0, "max": 550000.0, "title_prefix": "Senior Director"},
    14: {"min": 420000.0, "mid": 540000.0, "max": 660000.0, "title_prefix": "Vice President"},
    15: {"min": 500000.0, "mid": 650000.0, "max": 850000.0, "title_prefix": "Executive Officer (C-Suite)"},
}
