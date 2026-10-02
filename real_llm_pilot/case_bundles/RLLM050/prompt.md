# Bugs2Fix-stratified executable surrogate RLLM050

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public java.util.List < TYPE_1 > METHOD_1 ( int VAR_1 , TYPE_2 VAR_2 ) { return VAR_3 . METHOD_1 ( this . VAR_4 , VAR_2 ) ; } `

Source fixed method:
`public java.util.List < TYPE_1 > METHOD_1 ( int VAR_1 , TYPE_2 VAR_2 ) { return VAR_3 . METHOD_1 ( VAR_1 , VAR_2 ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["square_plus", "choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract", "multiply", "floor_divide_safe", "maximum"]`

Public examples:
```json
[
  {
    "x": 2,
    "y": 7,
    "expected": 11
  },
  {
    "x": 3,
    "y": -5,
    "expected": 4
  },
  {
    "x": 10,
    "y": 1,
    "expected": 101
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
