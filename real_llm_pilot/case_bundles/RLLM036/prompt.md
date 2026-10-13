# Beijing public-data microtask RLLM036

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `clean_feature` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Gucheng",
    "pm25": 9.0,
    "temperature": 11.7,
    "wind_speed": 2.2
  },
  {
    "station": "Gucheng",
    "pm25": 179.0,
    "temperature": 23.5,
    "wind_speed": 0.1
  },
  {
    "station": "Gucheng",
    "pm25": 10.0,
    "temperature": 24.3,
    "wind_speed": 0.6
  },
  {
    "station": "Gucheng",
    "pm25": 57.0,
    "temperature": 4.8,
    "wind_speed": 0.9
  },
  {
    "station": "Gucheng",
    "pm25": 228.0,
    "temperature": -3.0,
    "wind_speed": 0.8
  },
  {
    "station": "Gucheng",
    "pm25": 66.0,
    "temperature": 23.7,
    "wind_speed": 2.3
  },
  {
    "station": "Gucheng",
    "pm25": 175.0,
    "temperature": 27.5,
    "wind_speed": 0.0
  },
  {
    "station": "Gucheng",
    "pm25": 31.0,
    "temperature": 14.0,
    "wind_speed": 0.4
  },
  {
    "station": "Gucheng",
    "pm25": 124.0,
    "temperature": -1.1,
    "wind_speed": 0.8
  },
  {
    "station": "Gucheng",
    "pm25": 108.0,
    "temperature": 6.1,
    "wind_speed": 2.7
  },
  {
    "station": "Gucheng",
    "pm25": 16.0,
    "temperature": 30.3,
    "wind_speed": 1.5
  },
  {
    "station": "Gucheng",
    "pm25": 24.0,
    "temperature": 21.8,
    "wind_speed": 0.5
  },
  {
    "station": "Gucheng",
    "pm25": 44.0,
    "temperature": 10.1,
    "wind_speed": 0.7
  },
  {
    "station": "Gucheng",
    "pm25": 40.0,
    "temperature": 10.1,
    "wind_speed": 0.8
  },
  {
    "station": "Gucheng",
    "pm25": 11.0,
    "temperature": 0.0,
    "wind_speed": 2.7
  },
  {
    "station": "Gucheng",
    "pm25": 8.0,
    "temperature": 11.7,
    "wind_speed": 3.3
  },
  {
    "station": "Gucheng",
    "pm25": 228.0,
    "temperature": 27.3,
    "wind_speed": 1.7
  },
  {
    "station": "Gucheng",
    "pm25": 84.0,
    "temperature": 26.8,
    "wind_speed": 1.2
  },
  {
    "station": "Gucheng",
    "pm25": 238.0,
    "temperature": 5.7,
    "wind_speed": 1.5
  },
  {
    "station": "Gucheng",
    "pm25": 148.0,
    "temperature": -5.26,
    "wind_speed": 2.7
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 57.0,
    "prediction_A": 10.0,
    "prediction_B": 66.0
  },
  {
    "actual": 228.0,
    "prediction_A": 57.0,
    "prediction_B": 82.0
  },
  {
    "actual": 66.0,
    "prediction_A": 228.0,
    "prediction_B": 98.33
  },
  {
    "actual": 175.0,
    "prediction_A": 66.0,
    "prediction_B": 117.0
  },
  {
    "actual": 31.0,
    "prediction_A": 175.0,
    "prediction_B": 156.33
  },
  {
    "actual": 124.0,
    "prediction_A": 31.0,
    "prediction_B": 90.67
  },
  {
    "actual": 108.0,
    "prediction_A": 124.0,
    "prediction_B": 110.0
  },
  {
    "actual": 16.0,
    "prediction_A": 108.0,
    "prediction_B": 87.67
  },
  {
    "actual": 24.0,
    "prediction_A": 16.0,
    "prediction_B": 82.67
  },
  {
    "actual": 44.0,
    "prediction_A": 24.0,
    "prediction_B": 49.33
  },
  {
    "actual": 40.0,
    "prediction_A": 44.0,
    "prediction_B": 28.0
  },
  {
    "actual": 11.0,
    "prediction_A": 40.0,
    "prediction_B": 36.0
  },
  {
    "actual": 8.0,
    "prediction_A": 11.0,
    "prediction_B": 31.67
  },
  {
    "actual": 228.0,
    "prediction_A": 8.0,
    "prediction_B": 19.67
  },
  {
    "actual": 84.0,
    "prediction_A": 228.0,
    "prediction_B": 82.33
  },
  {
    "actual": 238.0,
    "prediction_A": 84.0,
    "prediction_B": 106.67
  },
  {
    "actual": 148.0,
    "prediction_A": 238.0,
    "prediction_B": 183.33
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
