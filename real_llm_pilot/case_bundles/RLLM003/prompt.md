# Adult public-data microtask RLLM003

Source: UCI Adult (48,842 records; CC BY 4.0). This case is a held-out
microtask for stage `validate_load` at preregistered difficulty D1.

Using only the records below, calculate every requested field. Treat `?` as
missing. Round means to 2 decimals, rates and F1 to 4 decimals. Model A predicts
positive when age >= sample median age AND education_num >= sample median.
Model B predicts positive when hours_per_week >= sample median hours OR
capital_gain > 0. F1 uses the positive class. If F1 ties, select model A.

Records:
```json
[
  {
    "age": 33,
    "education_num": 11,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 37,
    "education_num": 9,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 30,
    "education_num": 15,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 34,
    "education_num": 9,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 31,
    "education_num": 10,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 30,
    "education_num": 13,
    "hours_per_week": 45,
    "capital_gain": 13550,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 34,
    "education_num": 9,
    "hours_per_week": 42,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 31,
    "education_num": 10,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Self-emp-inc",
    "label": 0
  },
  {
    "age": 31,
    "education_num": 14,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 36,
    "education_num": 12,
    "hours_per_week": 44,
    "capital_gain": 7688,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 29,
    "education_num": 12,
    "hours_per_week": 45,
    "capital_gain": 0,
    "workclass": "State-gov",
    "label": 0
  },
  {
    "age": 36,
    "education_num": 13,
    "hours_per_week": 45,
    "capital_gain": 99999,
    "workclass": "Private",
    "label": 1
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>"}}`
Do not include calculations outside the JSON object.
