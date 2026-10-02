# Adult public-data microtask RLLM006

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
    "age": 50,
    "education_num": 9,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 55,
    "education_num": 9,
    "hours_per_week": 55,
    "capital_gain": 27828,
    "workclass": "Self-emp-not-inc",
    "label": 1
  },
  {
    "age": 56,
    "education_num": 14,
    "hours_per_week": 66,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 54,
    "education_num": 13,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 59,
    "education_num": 16,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 56,
    "education_num": 9,
    "hours_per_week": 55,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 67,
    "education_num": 16,
    "hours_per_week": 50,
    "capital_gain": 7896,
    "workclass": "Local-gov",
    "label": 1
  },
  {
    "age": 49,
    "education_num": 13,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 1
  },
  {
    "age": 51,
    "education_num": 10,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 50,
    "education_num": 14,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 51,
    "education_num": 9,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 52,
    "education_num": 14,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Local-gov",
    "label": 0
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>"}}`
Do not include calculations outside the JSON object.
