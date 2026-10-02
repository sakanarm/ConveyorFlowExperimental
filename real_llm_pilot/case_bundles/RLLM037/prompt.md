# Beijing public-data microtask RLLM037

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `clean_feature` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Shunyi",
    "pm25": 178.0,
    "temperature": 22.2,
    "wind_speed": 4.2
  },
  {
    "station": "Shunyi",
    "pm25": 144.0,
    "temperature": 31.5,
    "wind_speed": 1.2
  },
  {
    "station": "Shunyi",
    "pm25": 15.0,
    "temperature": 12.9,
    "wind_speed": 1.6
  },
  {
    "station": "Shunyi",
    "pm25": 21.0,
    "temperature": 14.5,
    "wind_speed": 1.8
  },
  {
    "station": "Shunyi",
    "pm25": 31.0,
    "temperature": 1.1,
    "wind_speed": 1.4
  },
  {
    "station": "Shunyi",
    "pm25": 40.0,
    "temperature": 6.9,
    "wind_speed": 0.5
  },
  {
    "station": "Shunyi",
    "pm25": 120.0,
    "temperature": 21.1,
    "wind_speed": 0.9
  },
  {
    "station": "Shunyi",
    "pm25": 85.0,
    "temperature": 30.9,
    "wind_speed": 2.8
  },
  {
    "station": "Shunyi",
    "pm25": 159.0,
    "temperature": 2.7,
    "wind_speed": 0.9
  },
  {
    "station": "Shunyi",
    "pm25": 92.0,
    "temperature": 3.0,
    "wind_speed": 1.3
  },
  {
    "station": "Shunyi",
    "pm25": 3.0,
    "temperature": 10.4,
    "wind_speed": 1.9
  },
  {
    "station": "Shunyi",
    "pm25": 151.0,
    "temperature": 23.1,
    "wind_speed": 1.2
  },
  {
    "station": "Shunyi",
    "pm25": 22.0,
    "temperature": 17.2,
    "wind_speed": 0.8
  },
  {
    "station": "Shunyi",
    "pm25": 105.0,
    "temperature": 2.0,
    "wind_speed": 1.0
  },
  {
    "station": "Shunyi",
    "pm25": 18.0,
    "temperature": -1.1,
    "wind_speed": 0.9
  },
  {
    "station": "Shunyi",
    "pm25": 16.0,
    "temperature": 14.7,
    "wind_speed": 0.8
  },
  {
    "station": "Shunyi",
    "pm25": 123.0,
    "temperature": 26.6,
    "wind_speed": 1.4
  },
  {
    "station": "Shunyi",
    "pm25": 14.0,
    "temperature": 17.32,
    "wind_speed": 2.5
  },
  {
    "station": "Shunyi",
    "pm25": 5.0,
    "temperature": 0.9,
    "wind_speed": 3.1
  },
  {
    "station": "Shunyi",
    "pm25": 48.0,
    "temperature": 0.3,
    "wind_speed": 1.4
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 21.0,
    "prediction_A": 15.0,
    "prediction_B": 112.33
  },
  {
    "actual": 31.0,
    "prediction_A": 21.0,
    "prediction_B": 60.0
  },
  {
    "actual": 40.0,
    "prediction_A": 31.0,
    "prediction_B": 22.33
  },
  {
    "actual": 120.0,
    "prediction_A": 40.0,
    "prediction_B": 30.67
  },
  {
    "actual": 85.0,
    "prediction_A": 120.0,
    "prediction_B": 63.67
  },
  {
    "actual": 159.0,
    "prediction_A": 85.0,
    "prediction_B": 81.67
  },
  {
    "actual": 92.0,
    "prediction_A": 159.0,
    "prediction_B": 121.33
  },
  {
    "actual": 3.0,
    "prediction_A": 92.0,
    "prediction_B": 112.0
  },
  {
    "actual": 151.0,
    "prediction_A": 3.0,
    "prediction_B": 84.67
  },
  {
    "actual": 22.0,
    "prediction_A": 151.0,
    "prediction_B": 82.0
  },
  {
    "actual": 105.0,
    "prediction_A": 22.0,
    "prediction_B": 58.67
  },
  {
    "actual": 18.0,
    "prediction_A": 105.0,
    "prediction_B": 92.67
  },
  {
    "actual": 16.0,
    "prediction_A": 18.0,
    "prediction_B": 48.33
  },
  {
    "actual": 123.0,
    "prediction_A": 16.0,
    "prediction_B": 46.33
  },
  {
    "actual": 14.0,
    "prediction_A": 123.0,
    "prediction_B": 52.33
  },
  {
    "actual": 5.0,
    "prediction_A": 14.0,
    "prediction_B": 51.0
  },
  {
    "actual": 48.0,
    "prediction_A": 5.0,
    "prediction_B": 47.33
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
