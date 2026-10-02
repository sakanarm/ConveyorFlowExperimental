# Beijing public-data microtask RLLM034

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `advanced_model` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 26.0,
    "temperature": 7.8,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 64.0,
    "temperature": 22.9,
    "wind_speed": 1.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 51.0,
    "temperature": 22.9,
    "wind_speed": 0.6
  },
  {
    "station": "Aotizhongxin",
    "pm25": 204.0,
    "temperature": 12.0,
    "wind_speed": 0.4
  },
  {
    "station": "Aotizhongxin",
    "pm25": 38.0,
    "temperature": 1.5,
    "wind_speed": 2.4
  },
  {
    "station": "Aotizhongxin",
    "pm25": 308.0,
    "temperature": 7.7,
    "wind_speed": 1.1
  },
  {
    "station": "Aotizhongxin",
    "pm25": 30.0,
    "temperature": 11.6,
    "wind_speed": 0.5
  },
  {
    "station": "Aotizhongxin",
    "pm25": 201.0,
    "temperature": 29.1,
    "wind_speed": 1.9
  },
  {
    "station": "Aotizhongxin",
    "pm25": 7.0,
    "temperature": 7.4,
    "wind_speed": 0.7
  },
  {
    "station": "Aotizhongxin",
    "pm25": 9.0,
    "temperature": -1.0,
    "wind_speed": 1.3
  },
  {
    "station": "Aotizhongxin",
    "pm25": 26.0,
    "temperature": 16.8,
    "wind_speed": 4.6
  },
  {
    "station": "Aotizhongxin",
    "pm25": 21.0,
    "temperature": 18.4,
    "wind_speed": 1.3
  },
  {
    "station": "Aotizhongxin",
    "pm25": 45.0,
    "temperature": 21.2,
    "wind_speed": 0.9
  },
  {
    "station": "Aotizhongxin",
    "pm25": 222.0,
    "temperature": 8.4,
    "wind_speed": 0.6
  },
  {
    "station": "Aotizhongxin",
    "pm25": 51.0,
    "temperature": -5.8,
    "wind_speed": 2.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 13.0,
    "temperature": 18.0,
    "wind_speed": 5.8
  },
  {
    "station": "Aotizhongxin",
    "pm25": 4.0,
    "temperature": 30.8,
    "wind_speed": 2.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 137.0,
    "temperature": 30.1,
    "wind_speed": 1.7
  },
  {
    "station": "Aotizhongxin",
    "pm25": 10.0,
    "temperature": 7.0,
    "wind_speed": 2.4
  },
  {
    "station": "Aotizhongxin",
    "pm25": 211.0,
    "temperature": -0.4,
    "wind_speed": 0.2
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 204.0,
    "prediction_A": 51.0,
    "prediction_B": 47.0
  },
  {
    "actual": 38.0,
    "prediction_A": 204.0,
    "prediction_B": 106.33
  },
  {
    "actual": 308.0,
    "prediction_A": 38.0,
    "prediction_B": 97.67
  },
  {
    "actual": 30.0,
    "prediction_A": 308.0,
    "prediction_B": 183.33
  },
  {
    "actual": 201.0,
    "prediction_A": 30.0,
    "prediction_B": 125.33
  },
  {
    "actual": 7.0,
    "prediction_A": 201.0,
    "prediction_B": 179.67
  },
  {
    "actual": 9.0,
    "prediction_A": 7.0,
    "prediction_B": 79.33
  },
  {
    "actual": 26.0,
    "prediction_A": 9.0,
    "prediction_B": 72.33
  },
  {
    "actual": 21.0,
    "prediction_A": 26.0,
    "prediction_B": 14.0
  },
  {
    "actual": 45.0,
    "prediction_A": 21.0,
    "prediction_B": 18.67
  },
  {
    "actual": 222.0,
    "prediction_A": 45.0,
    "prediction_B": 30.67
  },
  {
    "actual": 51.0,
    "prediction_A": 222.0,
    "prediction_B": 96.0
  },
  {
    "actual": 13.0,
    "prediction_A": 51.0,
    "prediction_B": 106.0
  },
  {
    "actual": 4.0,
    "prediction_A": 13.0,
    "prediction_B": 95.33
  },
  {
    "actual": 137.0,
    "prediction_A": 4.0,
    "prediction_B": 22.67
  },
  {
    "actual": 10.0,
    "prediction_A": 137.0,
    "prediction_B": 51.33
  },
  {
    "actual": 211.0,
    "prediction_A": 10.0,
    "prediction_B": 50.33
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
