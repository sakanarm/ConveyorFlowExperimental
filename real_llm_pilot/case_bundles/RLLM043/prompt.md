# Bugs2Fix-stratified executable surrogate RLLM043

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public boolean METHOD_1 ( android.view.View VAR_1 , TYPE_1 event ) { VAR_1 . METHOD_2 ( ) ; METHOD_3 ( VAR_1 ) ; return false ; } `

Source fixed method:
`public boolean METHOD_1 ( android.view.View VAR_1 , TYPE_1 event ) { METHOD_3 ( VAR_1 ) ; return false ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["distance_plus_one", "add", "subtract", "multiply"]`

Public examples:
```json
[
  {
    "x": -2,
    "y": -1,
    "expected": 2
  },
  {
    "x": -4,
    "y": -4,
    "expected": 1
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
