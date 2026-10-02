# Bugs2Fix-stratified executable surrogate RLLM041

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public TYPE_1 [ ] METHOD_1 ( ) { return ( ( TYPE_1 [ ] ) ( VAR_1 . METHOD_1 ( ) ) ) ; } `

Source fixed method:
`public TYPE_1 [ ] METHOD_1 ( ) { return VAR_1 . METHOD_1 ( new TYPE_1 [ size ( ) ] ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["modulo_safe", "square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one"]`

Public examples:
```json
[
  {
    "x": 8,
    "y": -3,
    "expected": -1
  },
  {
    "x": 10,
    "y": 5,
    "expected": 0
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
