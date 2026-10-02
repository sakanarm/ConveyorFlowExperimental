# Bugs2Fix-stratified executable surrogate RLLM042

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public long METHOD_1 ( ) { return TYPE_1 . METHOD_2 ( ( ( long ) ( VAR_1 . METHOD_1 ( ) ) ) ) ; } `

Source fixed method:
`public long METHOD_1 ( ) { return VAR_1 . METHOD_1 ( ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["floor_divide_safe", "maximum", "minimum", "absolute_difference"]`

Public examples:
```json
[
  {
    "x": 0,
    "y": -2,
    "expected": 0
  },
  {
    "x": -7,
    "y": 4,
    "expected": -2
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
