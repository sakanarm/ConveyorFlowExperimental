# Bugs2Fix-stratified executable surrogate RLLM055

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public java.util.List < TYPE_1 > METHOD_1 ( ) { return new java.util.LinkedList ( this . VAR_1 ) ; } `

Source fixed method:
`public java.util.List < TYPE_1 > METHOD_1 ( ) { return null ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["subtract", "multiply", "floor_divide_safe", "maximum", "minimum", "absolute_difference", "increment_by_one", "decrement_by_one", "clamp_nonnegative", "clamp_upper", "clamp_lower", "modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add"]`

Public examples:
```json
[
  {
    "x": -7,
    "y": -1,
    "expected": -6
  },
  {
    "x": 10,
    "y": 6,
    "expected": 4
  },
  {
    "x": -7,
    "y": 2,
    "expected": -9
  },
  {
    "x": 0,
    "y": 8,
    "expected": -8
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
