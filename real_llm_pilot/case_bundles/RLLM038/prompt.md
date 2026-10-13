# Beijing public-data microtask RLLM038

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `baseline_model` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Wanshouxigong",
    "pm25": 8.0,
    "temperature": 11.3,
    "wind_speed": 1.6
  },
  {
    "station": "Wanshouxigong",
    "pm25": 69.0,
    "temperature": 20.7,
    "wind_speed": 1.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 114.0,
    "temperature": 20.7,
    "wind_speed": 1.3
  },
  {
    "station": "Wanshouxigong",
    "pm25": 38.0,
    "temperature": 21.1,
    "wind_speed": 4.3
  },
  {
    "station": "Wanshouxigong",
    "pm25": 21.0,
    "temperature": 10.5,
    "wind_speed": 1.9
  },
  {
    "station": "Wanshouxigong",
    "pm25": 81.0,
    "temperature": -3.9,
    "wind_speed": 1.0
  },
  {
    "station": "Wanshouxigong",
    "pm25": 62.0,
    "temperature": 18.7,
    "wind_speed": 1.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 12.0,
    "temperature": 27.6,
    "wind_speed": 1.3
  },
  {
    "station": "Wanshouxigong",
    "pm25": 72.0,
    "temperature": 18.7,
    "wind_speed": 1.2
  },
  {
    "station": "Wanshouxigong",
    "pm25": 323.0,
    "temperature": 0.3,
    "wind_speed": 1.2
  },
  {
    "station": "Wanshouxigong",
    "pm25": 121.0,
    "temperature": 3.0,
    "wind_speed": 2.7
  },
  {
    "station": "Wanshouxigong",
    "pm25": 8.0,
    "temperature": 20.9,
    "wind_speed": 2.4
  },
  {
    "station": "Wanshouxigong",
    "pm25": 29.0,
    "temperature": 26.0,
    "wind_speed": 2.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 94.0,
    "temperature": 14.0,
    "wind_speed": 1.0
  },
  {
    "station": "Wanshouxigong",
    "pm25": 75.0,
    "temperature": 1.0,
    "wind_speed": 1.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 306.0,
    "temperature": 12.4,
    "wind_speed": 0.6
  },
  {
    "station": "Wanshouxigong",
    "pm25": 65.0,
    "temperature": 23.2,
    "wind_speed": 1.5
  },
  {
    "station": "Wanshouxigong",
    "pm25": 60.0,
    "temperature": 23.3,
    "wind_speed": 0.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 194.0,
    "temperature": 5.3,
    "wind_speed": 0.8
  },
  {
    "station": "Wanshouxigong",
    "pm25": 9.0,
    "temperature": -6.7,
    "wind_speed": 3.0
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 38.0,
    "prediction_A": 114.0,
    "prediction_B": 63.67
  },
  {
    "actual": 21.0,
    "prediction_A": 38.0,
    "prediction_B": 73.67
  },
  {
    "actual": 81.0,
    "prediction_A": 21.0,
    "prediction_B": 57.67
  },
  {
    "actual": 62.0,
    "prediction_A": 81.0,
    "prediction_B": 46.67
  },
  {
    "actual": 12.0,
    "prediction_A": 62.0,
    "prediction_B": 54.67
  },
  {
    "actual": 72.0,
    "prediction_A": 12.0,
    "prediction_B": 51.67
  },
  {
    "actual": 323.0,
    "prediction_A": 72.0,
    "prediction_B": 48.67
  },
  {
    "actual": 121.0,
    "prediction_A": 323.0,
    "prediction_B": 135.67
  },
  {
    "actual": 8.0,
    "prediction_A": 121.0,
    "prediction_B": 172.0
  },
  {
    "actual": 29.0,
    "prediction_A": 8.0,
    "prediction_B": 150.67
  },
  {
    "actual": 94.0,
    "prediction_A": 29.0,
    "prediction_B": 52.67
  },
  {
    "actual": 75.0,
    "prediction_A": 94.0,
    "prediction_B": 43.67
  },
  {
    "actual": 306.0,
    "prediction_A": 75.0,
    "prediction_B": 66.0
  },
  {
    "actual": 65.0,
    "prediction_A": 306.0,
    "prediction_B": 158.33
  },
  {
    "actual": 60.0,
    "prediction_A": 65.0,
    "prediction_B": 148.67
  },
  {
    "actual": 194.0,
    "prediction_A": 60.0,
    "prediction_B": 143.67
  },
  {
    "actual": 9.0,
    "prediction_A": 194.0,
    "prediction_B": 106.33
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
