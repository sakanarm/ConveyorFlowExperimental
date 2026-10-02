# Bugs2Fix-stratified executable surrogate RLLM051

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public static java.lang.String METHOD_1 ( java.lang.String VAR_1 ) { return VAR_1 . replaceAll ( VAR_2 , STRING_1 ) ; } `

Source fixed method:
`public static java.lang.String METHOD_1 ( java.lang.String VAR_1 ) { VAR_1 = VAR_1 . trim ( ) . replaceAll ( VAR_2 , STRING_1 ) ; return VAR_1 ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply", "floor_divide_safe"]`

Public examples:
```json
[
  {
    "x": 1,
    "y": -5,
    "expected": -4
  },
  {
    "x": 6,
    "y": -2,
    "expected": 0
  },
  {
    "x": -2,
    "y": 1,
    "expected": 0
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
