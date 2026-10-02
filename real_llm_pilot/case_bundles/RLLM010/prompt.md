# Adult public-data microtask RLLM010

Source: UCI Adult (48,842 records; CC BY 4.0). This case is a held-out
microtask for stage `baseline_model` at preregistered difficulty D2.

Using only the records below, calculate every requested field. Treat `?` as
missing. Round means to 2 decimals, rates and F1 to 4 decimals. Model A predicts
positive when age >= sample median age AND education_num >= sample median.
Model B predicts positive when hours_per_week >= sample median hours OR
capital_gain > 0. F1 uses the positive class. If F1 ties, select model A.

Records:
```json
[
  {
    "age": 48,
    "education_num": 11,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 44,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 48,
    "education_num": 9,
    "hours_per_week": 37,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 47,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 3103,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 38,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 43,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Federal-gov",
    "label": 1
  },
  {
    "age": 41,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 42,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 42,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Federal-gov",
    "label": 0
  },
  {
    "age": 42,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Federal-gov",
    "label": 0
  },
  {
    "age": 40,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 43,
    "education_num": 15,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Local-gov",
    "label": 1
  },
  {
    "age": 47,
    "education_num": 13,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 39,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 45,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 43,
    "education_num": 13,
    "hours_per_week": 40,
    "capital_gain": 3103,
    "workclass": "State-gov",
    "label": 1
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>", "mean_age": "<number>", "mean_hours_per_week": "<number>", "positive_rate": "<number>"}}`
Do not include calculations outside the JSON object.
