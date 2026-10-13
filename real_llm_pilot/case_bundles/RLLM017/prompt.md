# Adult public-data microtask RLLM017

Source: UCI Adult (48,842 records; CC BY 4.0). This case is a held-out
microtask for stage `advanced_model` at preregistered difficulty D3.

Using only the records below, calculate every requested field. Treat `?` as
missing. Round means to 2 decimals, rates and F1 to 4 decimals. Model A predicts
positive when age >= sample median age AND education_num >= sample median.
Model B predicts positive when hours_per_week >= sample median hours OR
capital_gain > 0. F1 uses the positive class. If F1 ties, select model A.

Records:
```json
[
  {
    "age": 34,
    "education_num": 9,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 35,
    "education_num": 13,
    "hours_per_week": 50,
    "capital_gain": 27828,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 29,
    "education_num": 9,
    "hours_per_week": 48,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 32,
    "education_num": 15,
    "hours_per_week": 50,
    "capital_gain": 15024,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 30,
    "education_num": 9,
    "hours_per_week": 72,
    "capital_gain": 0,
    "workclass": "State-gov",
    "label": 0
  },
  {
    "age": 33,
    "education_num": 7,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 34,
    "education_num": 10,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 32,
    "education_num": 13,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 37,
    "education_num": 10,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 36,
    "education_num": 10,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 34,
    "education_num": 10,
    "hours_per_week": 48,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 37,
    "education_num": 9,
    "hours_per_week": 68,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 34,
    "education_num": 14,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Self-emp-inc",
    "label": 1
  },
  {
    "age": 29,
    "education_num": 13,
    "hours_per_week": 55,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 33,
    "education_num": 10,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 35,
    "education_num": 11,
    "hours_per_week": 48,
    "capital_gain": 7298,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 36,
    "education_num": 10,
    "hours_per_week": 50,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 30,
    "education_num": 13,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 1
  },
  {
    "age": 32,
    "education_num": 11,
    "hours_per_week": 80,
    "capital_gain": 10520,
    "workclass": "Self-emp-inc",
    "label": 1
  },
  {
    "age": 37,
    "education_num": 15,
    "hours_per_week": 60,
    "capital_gain": 0,
    "workclass": "Self-emp-inc",
    "label": 1
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>", "mean_age": "<number>", "mean_hours_per_week": "<number>", "positive_rate": "<number>", "median_age": "<number>", "median_education_num": "<number>", "median_hours_per_week": "<number>", "model_a_f1": "<number>", "model_b_f1": "<number>", "selected_model": "<string>", "selected_confusion": {"tp": "<number>", "tn": "<number>", "fp": "<number>", "fn": "<number>"}}}`
Do not include calculations outside the JSON object.
