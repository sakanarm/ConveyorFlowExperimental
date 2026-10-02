# Adult public-data microtask RLLM002

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
    "age": 21,
    "education_num": 10,
    "hours_per_week": 54,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 27,
    "education_num": 10,
    "hours_per_week": 65,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 28,
    "education_num": 10,
    "hours_per_week": 55,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 22,
    "education_num": 9,
    "hours_per_week": 80,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 23,
    "education_num": 9,
    "hours_per_week": 50,
    "capital_gain": 4650,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 23,
    "education_num": 10,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 28,
    "education_num": 9,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 19,
    "education_num": 9,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 26,
    "education_num": 13,
    "hours_per_week": 90,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 27,
    "education_num": 9,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 27,
    "education_num": 13,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 23,
    "education_num": 10,
    "hours_per_week": 55,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>"}}`
Do not include calculations outside the JSON object.
