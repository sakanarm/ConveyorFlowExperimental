# Bugs2Fix-stratified executable surrogate RLLM059

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public static void remove ( int index ) { TYPE_1 . METHOD_1 ( ) . VAR_1 . remove ( index ) ; TYPE_2 . METHOD_2 ( ) . METHOD_3 ( new TYPE_3 ( false , false ) ) ; TYPE_1 . METHOD_4 ( ) ; } `

Source fixed method:
`public static void remove ( int index ) { TYPE_1 . METHOD_1 ( ) . VAR_1 . remove ( index ) ; TYPE_2 . METHOD_2 ( ) . METHOD_3 ( new TYPE_3 ( null , false , false ) ) ; TYPE_1 . METHOD_4 ( ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["increment_by_one", "decrement_by_one", "clamp_nonnegative", "clamp_upper", "clamp_lower", "modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply", "floor_divide_safe", "maximum", "minimum", "absolute_difference"]`

Public examples:
```json
[
  {
    "x": 2,
    "y": 8,
    "expected": 3
  },
  {
    "x": -3,
    "y": 7,
    "expected": -2
  },
  {
    "x": 4,
    "y": 2,
    "expected": 5
  },
  {
    "x": 5,
    "y": -1,
    "expected": 6
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
