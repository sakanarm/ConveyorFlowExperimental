# Adult public-data microtask RLLM001

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
    "age": 28,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 27,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 21,
    "education_num": 9,
    "hours_per_week": 10,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 18,
    "education_num": 10,
    "hours_per_week": 30,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 25,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 2597,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 20,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 24,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 26,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 18,
    "education_num": 7,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 28,
    "education_num": 12,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 23,
    "education_num": 13,
    "hours_per_week": 7,
    "capital_gain": 0,
    "workclass": "State-gov",
    "label": 0
  },
  {
    "age": 19,
    "education_num": 10,
    "hours_per_week": 35,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>"}}`
Do not include calculations outside the JSON object.
