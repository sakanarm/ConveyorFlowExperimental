# Bugs2Fix-stratified executable surrogate RLLM047

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public boolean METHOD_1 ( int VAR_1 , int VAR_2 , int VAR_3 ) { return true ; } `

Source fixed method:
`public boolean METHOD_1 ( int VAR_1 , int VAR_2 , int VAR_3 ) { return false ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply", "floor_divide_safe", "maximum"]`

Public examples:
```json
[
  {
    "x": -1,
    "y": 8,
    "expected": 9
  },
  {
    "x": 11,
    "y": 8,
    "expected": 129
  },
  {
    "x": 8,
    "y": -5,
    "expected": 59
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
