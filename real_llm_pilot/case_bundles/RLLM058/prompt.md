# Bugs2Fix-stratified executable surrogate RLLM058

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public void METHOD_1 ( ) { if ( ( ( ( VAR_1 ) != null ) && ( ! ( VAR_1 . METHOD_2 ( ) ) ) ) && ( ! ( VAR_1 . METHOD_3 ( ) ) ) ) { VAR_1 . METHOD_4 ( true ) ; } } `

Source fixed method:
`public void METHOD_1 ( ) { if ( ( VAR_1 ) != null ) { VAR_1 . METHOD_4 ( true ) ; } } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply", "floor_divide_safe", "maximum", "minimum", "absolute_difference", "increment_by_one", "decrement_by_one", "clamp_nonnegative", "clamp_upper", "clamp_lower", "modulo_safe", "square_plus"]`

Public examples:
```json
[
  {
    "x": 8,
    "y": 2,
    "expected": 8
  },
  {
    "x": 8,
    "y": 8,
    "expected": 8
  },
  {
    "x": -6,
    "y": -2,
    "expected": -6
  },
  {
    "x": -5,
    "y": 0,
    "expected": -5
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
