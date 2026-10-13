# Beijing public-data microtask RLLM035

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `evaluate` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Dingling",
    "pm25": 48.0,
    "temperature": 14.5,
    "wind_speed": 1.7
  },
  {
    "station": "Dingling",
    "pm25": 16.0,
    "temperature": 30.3,
    "wind_speed": 2.0
  },
  {
    "station": "Dingling",
    "pm25": 17.0,
    "temperature": 22.6,
    "wind_speed": 1.1
  },
  {
    "station": "Dingling",
    "pm25": 31.0,
    "temperature": 8.7,
    "wind_speed": 1.8
  },
  {
    "station": "Dingling",
    "pm25": 7.0,
    "temperature": -4.4,
    "wind_speed": 2.4
  },
  {
    "station": "Dingling",
    "pm25": 330.0,
    "temperature": 15.9,
    "wind_speed": 2.2
  },
  {
    "station": "Dingling",
    "pm25": 8.0,
    "temperature": 23.9,
    "wind_speed": 1.1
  },
  {
    "station": "Dingling",
    "pm25": 66.0,
    "temperature": 28.0,
    "wind_speed": 0.9
  },
  {
    "station": "Dingling",
    "pm25": 7.0,
    "temperature": 0.6,
    "wind_speed": 1.2
  },
  {
    "station": "Dingling",
    "pm25": 60.0,
    "temperature": -5.0,
    "wind_speed": 1.7
  },
  {
    "station": "Dingling",
    "pm25": 51.0,
    "temperature": 12.0,
    "wind_speed": 1.0
  },
  {
    "station": "Dingling",
    "pm25": 16.0,
    "temperature": 19.2,
    "wind_speed": 1.3
  },
  {
    "station": "Dingling",
    "pm25": 12.0,
    "temperature": 27.3,
    "wind_speed": 3.1
  },
  {
    "station": "Dingling",
    "pm25": 199.0,
    "temperature": -0.7,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 4.0,
    "temperature": -7.6,
    "wind_speed": 1.9
  },
  {
    "station": "Dingling",
    "pm25": 169.0,
    "temperature": 29.4,
    "wind_speed": 3.6
  },
  {
    "station": "Dingling",
    "pm25": 189.0,
    "temperature": 30.1,
    "wind_speed": 2.9
  },
  {
    "station": "Dingling",
    "pm25": 18.0,
    "temperature": 20.0,
    "wind_speed": 0.6
  },
  {
    "station": "Dingling",
    "pm25": 152.0,
    "temperature": 23.3,
    "wind_speed": 1.9
  },
  {
    "station": "Dingling",
    "pm25": 11.0,
    "temperature": 4.0,
    "wind_speed": 4.7
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 31.0,
    "prediction_A": 17.0,
    "prediction_B": 27.0
  },
  {
    "actual": 7.0,
    "prediction_A": 31.0,
    "prediction_B": 21.33
  },
  {
    "actual": 330.0,
    "prediction_A": 7.0,
    "prediction_B": 18.33
  },
  {
    "actual": 8.0,
    "prediction_A": 330.0,
    "prediction_B": 122.67
  },
  {
    "actual": 66.0,
    "prediction_A": 8.0,
    "prediction_B": 115.0
  },
  {
    "actual": 7.0,
    "prediction_A": 66.0,
    "prediction_B": 134.67
  },
  {
    "actual": 60.0,
    "prediction_A": 7.0,
    "prediction_B": 27.0
  },
  {
    "actual": 51.0,
    "prediction_A": 60.0,
    "prediction_B": 44.33
  },
  {
    "actual": 16.0,
    "prediction_A": 51.0,
    "prediction_B": 39.33
  },
  {
    "actual": 12.0,
    "prediction_A": 16.0,
    "prediction_B": 42.33
  },
  {
    "actual": 199.0,
    "prediction_A": 12.0,
    "prediction_B": 26.33
  },
  {
    "actual": 4.0,
    "prediction_A": 199.0,
    "prediction_B": 75.67
  },
  {
    "actual": 169.0,
    "prediction_A": 4.0,
    "prediction_B": 71.67
  },
  {
    "actual": 189.0,
    "prediction_A": 169.0,
    "prediction_B": 124.0
  },
  {
    "actual": 18.0,
    "prediction_A": 189.0,
    "prediction_B": 120.67
  },
  {
    "actual": 152.0,
    "prediction_A": 18.0,
    "prediction_B": 125.33
  },
  {
    "actual": 11.0,
    "prediction_A": 152.0,
    "prediction_B": 119.67
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
