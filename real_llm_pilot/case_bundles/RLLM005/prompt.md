# Adult public-data microtask RLLM005

Source: UCI Adult (48,842 records; CC BY 4.0). This case is a held-out
microtask for stage `report` at preregistered difficulty D1.

Using only the records below, calculate every requested field. Treat `?` as
missing. Round means to 2 decimals, rates and F1 to 4 decimals. Model A predicts
positive when age >= sample median age AND education_num >= sample median.
Model B predicts positive when hours_per_week >= sample median hours OR
capital_gain > 0. F1 uses the positive class. If F1 ties, select model A.

Records:
```json
[
  {
    "age": 68,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 59,
    "education_num": 16,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 54,
    "education_num": 10,
    "hours_per_week": 40,
    "capital_gain": 3103,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 54,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Local-gov",
    "label": 0
  },
  {
    "age": 80,
    "education_num": 9,
    "hours_per_week": 20,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 51,
    "education_num": 14,
    "hours_per_week": 40,
    "capital_gain": 15024,
    "workclass": "Local-gov",
    "label": 1
  },
  {
    "age": 68,
    "education_num": 9,
    "hours_per_week": 8,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 65,
    "education_num": 7,
    "hours_per_week": 29,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 67,
    "education_num": 10,
    "hours_per_week": 4,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 65,
    "education_num": 13,
    "hours_per_week": 30,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 64,
    "education_num": 10,
    "hours_per_week": 12,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 53,
    "education_num": 13,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>"}}`
Do not include calculations outside the JSON object.
