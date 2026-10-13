# Adult public-data microtask RLLM012

Source: UCI Adult (48,842 records; CC BY 4.0). This case is a held-out
microtask for stage `evaluate` at preregistered difficulty D2.

Using only the records below, calculate every requested field. Treat `?` as
missing. Round means to 2 decimals, rates and F1 to 4 decimals. Model A predicts
positive when age >= sample median age AND education_num >= sample median.
Model B predicts positive when hours_per_week >= sample median hours OR
capital_gain > 0. F1 uses the positive class. If F1 ties, select model A.

Records:
```json
[
  {
    "age": 52,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 49,
    "education_num": 14,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 51,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 66,
    "education_num": 13,
    "hours_per_week": 30,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 58,
    "education_num": 13,
    "hours_per_week": 37,
    "capital_gain": 0,
    "workclass": "Local-gov",
    "label": 0
  },
  {
    "age": 61,
    "education_num": 10,
    "hours_per_week": 30,
    "capital_gain": 99999,
    "workclass": "?",
    "label": 1
  },
  {
    "age": 65,
    "education_num": 13,
    "hours_per_week": 20,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 54,
    "education_num": 13,
    "hours_per_week": 40,
    "capital_gain": 15024,
    "workclass": "Self-emp-inc",
    "label": 1
  },
  {
    "age": 90,
    "education_num": 2,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 63,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 60,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Local-gov",
    "label": 0
  },
  {
    "age": 59,
    "education_num": 14,
    "hours_per_week": 15,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 74,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 15831,
    "workclass": "State-gov",
    "label": 1
  },
  {
    "age": 60,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 63,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 58,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>", "mean_age": "<number>", "mean_hours_per_week": "<number>", "positive_rate": "<number>"}}`
Do not include calculations outside the JSON object.
