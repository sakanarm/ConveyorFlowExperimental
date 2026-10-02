# Adult public-data microtask RLLM014

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
    "age": 28,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "State-gov",
    "label": 0
  },
  {
    "age": 28,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 19,
    "education_num": 9,
    "hours_per_week": 24,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 21,
    "education_num": 9,
    "hours_per_week": 22,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 28,
    "education_num": 7,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 25,
    "education_num": 6,
    "hours_per_week": 24,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 23,
    "education_num": 12,
    "hours_per_week": 16,
    "capital_gain": 0,
    "workclass": "?",
    "label": 0
  },
  {
    "age": 25,
    "education_num": 11,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Self-emp-not-inc",
    "label": 0
  },
  {
    "age": 25,
    "education_num": 13,
    "hours_per_week": 37,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 26,
    "education_num": 10,
    "hours_per_week": 20,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 25,
    "education_num": 9,
    "hours_per_week": 28,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 22,
    "education_num": 7,
    "hours_per_week": 25,
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
    "age": 27,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 19,
    "education_num": 10,
    "hours_per_week": 30,
    "capital_gain": 0,
    "workclass": "Local-gov",
    "label": 0
  },
  {
    "age": 21,
    "education_num": 9,
    "hours_per_week": 25,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 21,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 28,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 2105,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 19,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  },
  {
    "age": 23,
    "education_num": 9,
    "hours_per_week": 40,
    "capital_gain": 0,
    "workclass": "Private",
    "label": 0
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "positive_count": "<number>", "missing_workclass_count": "<number>", "mean_age": "<number>", "mean_hours_per_week": "<number>", "positive_rate": "<number>", "median_age": "<number>", "median_education_num": "<number>", "median_hours_per_week": "<number>", "model_a_f1": "<number>", "model_b_f1": "<number>", "selected_model": "<string>", "selected_confusion": {"tp": "<number>", "tn": "<number>", "fp": "<number>", "fn": "<number>"}}}`
Do not include calculations outside the JSON object.
