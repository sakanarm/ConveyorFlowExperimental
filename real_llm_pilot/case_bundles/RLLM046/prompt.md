# Bugs2Fix-stratified executable surrogate RLLM046

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public void METHOD_1 ( java.lang.Throwable VAR_1 ) { TYPE_1 . METHOD_2 ( VAR_2 , STRING_1 ) ; if ( 0 != VAR_3 ) { VAR_4 . METHOD_3 ( VAR_5 . METHOD_4 ( VAR_3 ) ) ; VAR_4 . METHOD_5 ( VAR_6 , VAR_7 ) ; } } `

Source fixed method:
`public void METHOD_1 ( java.lang.Throwable VAR_1 ) { if ( 0 != VAR_3 ) { VAR_4 . METHOD_3 ( VAR_5 . METHOD_4 ( VAR_3 ) ) ; VAR_4 . METHOD_5 ( VAR_6 , VAR_7 ) ; } } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["choose_x_if_nonzero_else_y", "distance_plus_one", "add", "subtract"]`

Public examples:
```json
[
  {
    "x": 10,
    "y": 8,
    "expected": 10
  },
  {
    "x": -6,
    "y": -2,
    "expected": -6
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
