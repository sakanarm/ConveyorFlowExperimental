# Beijing public-data microtask RLLM040

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `evaluate` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 359.0,
    "temperature": 18.1,
    "wind_speed": 0.4
  },
  {
    "station": "Changping",
    "pm25": 47.0,
    "temperature": -0.5,
    "wind_speed": 0.6
  },
  {
    "station": "Changping",
    "pm25": 91.0,
    "temperature": 9.2,
    "wind_speed": 1.2
  },
  {
    "station": "Dingling",
    "pm25": 75.0,
    "temperature": 6.9,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 81.0,
    "temperature": 8.5,
    "wind_speed": 2.0
  },
  {
    "station": "Dongsi",
    "pm25": 15.0,
    "temperature": 18.1,
    "wind_speed": 1.9
  },
  {
    "station": "Dongsi",
    "pm25": 37.0,
    "temperature": 4.1,
    "wind_speed": 1.0
  },
  {
    "station": "Guanyuan",
    "pm25": 171.0,
    "temperature": 15.7,
    "wind_speed": 1.6
  },
  {
    "station": "Guanyuan",
    "pm25": 6.0,
    "temperature": 3.3,
    "wind_speed": 1.7
  },
  {
    "station": "Gucheng",
    "pm25": 86.0,
    "temperature": 11.8,
    "wind_speed": 0.0
  },
  {
    "station": "Huairou",
    "pm25": 135.0,
    "temperature": -1.1,
    "wind_speed": 0.9
  },
  {
    "station": "Huairou",
    "pm25": 101.0,
    "temperature": 9.4,
    "wind_speed": 1.3
  },
  {
    "station": "Nongzhanguan",
    "pm25": 375.0,
    "temperature": -1.0,
    "wind_speed": 0.8
  },
  {
    "station": "Shunyi",
    "pm25": 153.0,
    "temperature": 5.0,
    "wind_speed": 0.8
  },
  {
    "station": "Shunyi",
    "pm25": 40.0,
    "temperature": -2.7,
    "wind_speed": 1.0
  },
  {
    "station": "Tiantan",
    "pm25": 172.0,
    "temperature": 11.3,
    "wind_speed": 0.7
  },
  {
    "station": "Tiantan",
    "pm25": 403.0,
    "temperature": 1.2,
    "wind_speed": 1.2
  },
  {
    "station": "Wanliu",
    "pm25": 228.0,
    "temperature": 10.4,
    "wind_speed": 0.7
  },
  {
    "station": "Wanshouxigong",
    "pm25": 108.0,
    "temperature": -9.2,
    "wind_speed": 0.9
  },
  {
    "station": "Wanshouxigong",
    "pm25": 12.0,
    "temperature": 11.7,
    "wind_speed": 3.1
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 75.0,
    "prediction_A": 91.0,
    "prediction_B": 165.67
  },
  {
    "actual": 81.0,
    "prediction_A": 75.0,
    "prediction_B": 71.0
  },
  {
    "actual": 15.0,
    "prediction_A": 81.0,
    "prediction_B": 82.33
  },
  {
    "actual": 37.0,
    "prediction_A": 15.0,
    "prediction_B": 57.0
  },
  {
    "actual": 171.0,
    "prediction_A": 37.0,
    "prediction_B": 44.33
  },
  {
    "actual": 6.0,
    "prediction_A": 171.0,
    "prediction_B": 74.33
  },
  {
    "actual": 86.0,
    "prediction_A": 6.0,
    "prediction_B": 71.33
  },
  {
    "actual": 135.0,
    "prediction_A": 86.0,
    "prediction_B": 87.67
  },
  {
    "actual": 101.0,
    "prediction_A": 135.0,
    "prediction_B": 75.67
  },
  {
    "actual": 375.0,
    "prediction_A": 101.0,
    "prediction_B": 107.33
  },
  {
    "actual": 153.0,
    "prediction_A": 375.0,
    "prediction_B": 203.67
  },
  {
    "actual": 40.0,
    "prediction_A": 153.0,
    "prediction_B": 209.67
  },
  {
    "actual": 172.0,
    "prediction_A": 40.0,
    "prediction_B": 189.33
  },
  {
    "actual": 403.0,
    "prediction_A": 172.0,
    "prediction_B": 121.67
  },
  {
    "actual": 228.0,
    "prediction_A": 403.0,
    "prediction_B": 205.0
  },
  {
    "actual": 108.0,
    "prediction_A": 228.0,
    "prediction_B": 267.67
  },
  {
    "actual": 12.0,
    "prediction_A": 108.0,
    "prediction_B": 246.33
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
