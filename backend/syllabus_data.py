"""
Static syllabus reference data used by study_plan.py to build
day-by-day plans. `weightage` is an approximate relative importance
score (higher = more exam marks / more frequently tested), not an
official NTA/NMC figure — used only to prioritise topic ordering.

Extend this over time; it does not need to be exhaustive on day one.
"""

JEE_MAIN = {
    "Physics": [
        {"name": "Units, Dimensions & Errors", "weightage": 3},
        {"name": "Kinematics", "weightage": 6},
        {"name": "Laws of Motion", "weightage": 6},
        {"name": "Work, Energy & Power", "weightage": 5},
        {"name": "Rotational Motion", "weightage": 6},
        {"name": "Gravitation", "weightage": 4},
        {"name": "Mechanical Properties of Matter", "weightage": 4},
        {"name": "Thermodynamics", "weightage": 6},
        {"name": "Kinetic Theory of Gases", "weightage": 3},
        {"name": "Oscillations & Waves", "weightage": 6},
        {"name": "Electrostatics", "weightage": 7},
        {"name": "Current Electricity", "weightage": 7},
        {"name": "Magnetic Effects of Current", "weightage": 5},
        {"name": "Electromagnetic Induction & AC", "weightage": 5},
        {"name": "Ray & Wave Optics", "weightage": 6},
        {"name": "Modern Physics (Atoms, Nuclei, Dual Nature)", "weightage": 6},
        {"name": "Semiconductor Electronics", "weightage": 4},
    ],
    "Chemistry": [
        {"name": "Mole Concept & Stoichiometry", "weightage": 5},
        {"name": "Atomic Structure", "weightage": 5},
        {"name": "Chemical Bonding", "weightage": 6},
        {"name": "States of Matter & Thermodynamics", "weightage": 5},
        {"name": "Equilibrium (Chemical & Ionic)", "weightage": 6},
        {"name": "Redox & Electrochemistry", "weightage": 5},
        {"name": "Chemical Kinetics", "weightage": 4},
        {"name": "Periodic Table & Periodicity", "weightage": 4},
        {"name": "s-Block & p-Block Elements", "weightage": 6},
        {"name": "d & f Block, Coordination Compounds", "weightage": 5},
        {"name": "GOC & Isomerism", "weightage": 5},
        {"name": "Hydrocarbons", "weightage": 4},
        {"name": "Haloalkanes, Alcohols, Phenols, Ethers", "weightage": 5},
        {"name": "Aldehydes, Ketones, Carboxylic Acids", "weightage": 5},
        {"name": "Amines & Biomolecules", "weightage": 4},
        {"name": "Practical & Environmental Chemistry", "weightage": 3},
    ],
    "Mathematics": [
        {"name": "Sets, Relations & Functions", "weightage": 4},
        {"name": "Complex Numbers & Quadratic Equations", "weightage": 5},
        {"name": "Matrices & Determinants", "weightage": 5},
        {"name": "Permutations, Combinations & Binomial Theorem", "weightage": 5},
        {"name": "Sequences & Series", "weightage": 4},
        {"name": "Limits, Continuity & Differentiability", "weightage": 6},
        {"name": "Application of Derivatives", "weightage": 5},
        {"name": "Integral Calculus", "weightage": 6},
        {"name": "Differential Equations", "weightage": 4},
        {"name": "Coordinate Geometry (Line, Circle, Conics)", "weightage": 7},
        {"name": "Three Dimensional Geometry", "weightage": 4},
        {"name": "Vector Algebra", "weightage": 4},
        {"name": "Statistics & Probability", "weightage": 4},
        {"name": "Trigonometry", "weightage": 4},
    ],
}

# JEE Advanced reuses JEE Main topics but weighted toward
# higher-order/multi-concept areas; kept separate so it can diverge later.
JEE_ADVANCED = JEE_MAIN

NEET = {
    "Physics": JEE_MAIN["Physics"],  # NEET physics syllabus overlaps heavily with JEE Main
    "Chemistry": JEE_MAIN["Chemistry"],
    "Biology": [
        {"name": "Diversity of Living Organisms", "weightage": 5},
        {"name": "Cell Structure & Function", "weightage": 6},
        {"name": "Plant Physiology", "weightage": 6},
        {"name": "Human Physiology", "weightage": 8},
        {"name": "Reproduction (Plants & Humans)", "weightage": 6},
        {"name": "Genetics & Evolution", "weightage": 7},
        {"name": "Biology & Human Welfare", "weightage": 4},
        {"name": "Biotechnology & Applications", "weightage": 5},
        {"name": "Ecology & Environment", "weightage": 6},
        {"name": "Structural Organisation in Animals", "weightage": 3},
    ],
}

SYLLABUS = {
    "JEE Main": JEE_MAIN,
    "JEE Advanced": JEE_ADVANCED,
    "NEET": NEET,
}

# Free, well-known resources to point students to alongside SATHEE.
# Keep this list to genuinely free, reputable sources.
DEFAULT_RESOURCES = [
    "SATHEE lecture videos + topic-wise practice test for today's topics (sathee.iitk.ac.in)",
    "NCERT textbook chapter (primary source for both JEE and NEET)",
    "SATHEE's Previous Year Questions archive (sathee.iitk.ac.in/jee-pyq) for JEE, or NEET PYQ archives",
]

# Per-exam links into SATHEE's own site sections, used in onboarding replies
# and the study plan so students land on the right track's page.
SATHEE_LINKS = {
    "JEE Main": "https://sathee.iitk.ac.in/sathee-jee/",
    "JEE Advanced": "https://sathee.iitk.ac.in/sathee-jee/",
    "NEET": "https://sathee.iitk.ac.in/",  # site nav has a dedicated Medical/NEET section
}

EXAM_LABELS = {
    "JEE Main": "JEE Main",
    "JEE Advanced": "JEE Advanced",
    "NEET": "NEET (UG)",
}
