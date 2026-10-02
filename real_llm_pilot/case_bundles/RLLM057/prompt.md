# Bugs2Fix-stratified executable surrogate RLLM057

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public int METHOD_1 ( int VAR_1 ) { java.util.Random VAR_2 = new java.util.Random ( ) ; VAR_3 = ( VAR_2 . METHOD_2 ( VAR_1 ) ) + 1 ; return VAR_3 ; } `

Source fixed method:
`public void METHOD_1 ( int VAR_1 ) { java.util.Random VAR_2 = new java.util.Random ( ) ; this . VAR_3 = ( VAR_2 . METHOD_2 ( VAR_1 ) ) + 1 ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["subtract", "multiply", "floor_divide_safe", "maximum", "minimum", "absolute_difference", "increment_by_one", "decrement_by_one", "clamp_nonnegative", "clamp_upper", "clamp_lower", "modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add"]`

Public examples:
```json
[
  {
    "x": -5,
    "y": 0,
    "expected": -5
  },
  {
    "x": 10,
    "y": 0,
    "expected": 10
  },
  {
    "x": 2,
    "y": -2,
    "expected": 4
  },
  {
    "x": 8,
    "y": 9,
    "expected": -1
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
