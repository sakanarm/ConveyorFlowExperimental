# Bugs2Fix-stratified executable surrogate RLLM049

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public boolean remove ( int ... VAR_1 ) { return remove ( METHOD_1 ( VAR_1 ) ) ; } `

Source fixed method:
`public boolean contains ( int ... keys ) throws java.lang.Exception { return ( METHOD_1 ( keys ) ) >= 0 ? true : false ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["clamp_lower", "modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply"]`

Public examples:
```json
[
  {
    "x": -2,
    "y": -2,
    "expected": -2
  },
  {
    "x": 11,
    "y": 8,
    "expected": 11
  },
  {
    "x": -1,
    "y": -4,
    "expected": -1
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
