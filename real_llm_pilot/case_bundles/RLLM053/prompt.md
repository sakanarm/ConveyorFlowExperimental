# Bugs2Fix-stratified executable surrogate RLLM053

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`public void METHOD_1 ( int VAR_1 , TYPE_1 [ ] VAR_2 , TYPE_2 response ) { TYPE_3 . METHOD_2 ( context , ( ( STRING_1 + response ) + STRING_2 ) , VAR_3 ) . show ( ) ; METHOD_3 ( ) ; } `

Source fixed method:
`public void METHOD_1 ( int VAR_1 , TYPE_1 [ ] VAR_2 , TYPE_2 response ) { TYPE_3 . METHOD_2 ( context , ( ( STRING_1 + response ) + STRING_2 ) , VAR_3 ) . show ( ) ; } `

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`["minimum", "absolute_difference", "increment_by_one", "decrement_by_one", "clamp_nonnegative", "clamp_upper", "clamp_lower", "modulo_safe"]`

Public examples:
```json
[
  {
    "x": 4,
    "y": 2,
    "expected": 2
  },
  {
    "x": -2,
    "y": 0,
    "expected": -2
  },
  {
    "x": -1,
    "y": -1,
    "expected": -1
  }
]
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{"answer": {"repair_action": "one_candidate_action"}}`
