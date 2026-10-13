# Bugs2Fix-stratified executable surrogate RLLM056

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public static void METHOD_1 ( java.lang.String VAR_1 , java.lang.Long VAR_2 ) { VAR_3 . put ( VAR_1 , VAR_2 ) ; } `

Source fixed method:
`public static void METHOD_1 ( java.lang.String VAR_1 , java.lang.Long VAR_2 ) { if ( null == VAR_1 ) { return ; } VAR_3 . put ( VAR_1 , VAR_2 ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["maximum", "minimum", "absolute_difference", "increment_by_one", "decrement_by_one", "clamp_nonnegative", "clamp_upper", "clamp_lower", "modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply", "floor_divide_safe"]`

Public examples:
```json
[
  {
    "x": 11,
    "y": -1,
    "expected": 11
  },
  {
    "x": -1,
    "y": 6,
    "expected": 6
  },
  {
    "x": 7,
    "y": 6,
    "expected": 7
  },
  {
    "x": 2,
    "y": -4,
    "expected": 2
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
