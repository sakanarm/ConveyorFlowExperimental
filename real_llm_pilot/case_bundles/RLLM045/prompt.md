# Bugs2Fix-stratified executable surrogate RLLM045

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`protected void METHOD_1 ( TYPE_1 VAR_1 ) { super . METHOD_1 ( VAR_1 ) ; TYPE_2 . METHOD_2 ( VAR_2 , STRING_1 ) ; TYPE_3 . METHOD_3 ( METHOD_4 ( ) ) ; METHOD_5 ( ) ; METHOD_6 ( ) ; } `

Source fixed method:
`protected void METHOD_1 ( TYPE_1 VAR_1 ) { super . METHOD_1 ( VAR_1 ) ; TYPE_2 . METHOD_2 ( VAR_2 , STRING_1 ) ; TYPE_3 . METHOD_3 ( METHOD_4 ( ) ) ; METHOD_6 ( ) ; METHOD_5 ( ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["distance_plus_one", "add", "subtract", "multiply"]`

Public examples:
```json
[
  {
    "x": -2,
    "y": 2,
    "expected": 5
  },
  {
    "x": 2,
    "y": 0,
    "expected": 3
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
