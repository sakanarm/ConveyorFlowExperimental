# Beijing public-data microtask RLLM039

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `eda` microtask at preregistered difficulty D3.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 46.0,
    "temperature": 25.3,
    "wind_speed": 3.3
  },
  {
    "station": "Changping",
    "pm25": 158.0,
    "temperature": 20.1,
    "wind_speed": 0.1
  },
  {
    "station": "Changping",
    "pm25": 56.0,
    "temperature": 26.5,
    "wind_speed": 3.8
  },
  {
    "station": "Changping",
    "pm25": 34.0,
    "temperature": 24.4,
    "wind_speed": 3.6
  },
  {
    "station": "Dingling",
    "pm25": 15.0,
    "temperature": 23.2,
    "wind_speed": 1.8
  },
  {
    "station": "Dongsi",
    "pm25": 116.0,
    "temperature": 10.1,
    "wind_speed": 1.6
  },
  {
    "station": "Dongsi",
    "pm25": 90.0,
    "temperature": 28.6,
    "wind_speed": 3.3
  },
  {
    "station": "Guanyuan",
    "pm25": 77.0,
    "temperature": 12.8,
    "wind_speed": 1.1
  },
  {
    "station": "Guanyuan",
    "pm25": 36.0,
    "temperature": 20.4,
    "wind_speed": 2.0
  },
  {
    "station": "Gucheng",
    "pm25": 46.0,
    "temperature": 23.8,
    "wind_speed": 1.7
  },
  {
    "station": "Huairou",
    "pm25": 13.0,
    "temperature": 24.2,
    "wind_speed": 1.3
  },
  {
    "station": "Huairou",
    "pm25": 90.0,
    "temperature": 16.9,
    "wind_speed": 1.7
  },
  {
    "station": "Nongzhanguan",
    "pm25": 14.0,
    "temperature": 15.8,
    "wind_speed": 3.1
  },
  {
    "station": "Shunyi",
    "pm25": 68.0,
    "temperature": 25.4,
    "wind_speed": 4.8
  },
  {
    "station": "Shunyi",
    "pm25": 74.0,
    "temperature": 10.8,
    "wind_speed": 1.9
  },
  {
    "station": "Tiantan",
    "pm25": 98.0,
    "temperature": 21.8,
    "wind_speed": 2.8
  },
  {
    "station": "Wanliu",
    "pm25": 11.0,
    "temperature": 9.5,
    "wind_speed": 5.2
  },
  {
    "station": "Wanliu",
    "pm25": 192.0,
    "temperature": 23.5,
    "wind_speed": 1.6
  },
  {
    "station": "Wanshouxigong",
    "pm25": 158.0,
    "temperature": 8.9,
    "wind_speed": 0.0
  },
  {
    "station": "Wanshouxigong",
    "pm25": 23.0,
    "temperature": 26.9,
    "wind_speed": 2.7
  }
]
```
Forecast rows:
```json
[
  {
    "actual": 34.0,
    "prediction_A": 56.0,
    "prediction_B": 86.67
  },
  {
    "actual": 15.0,
    "prediction_A": 34.0,
    "prediction_B": 82.67
  },
  {
    "actual": 116.0,
    "prediction_A": 15.0,
    "prediction_B": 35.0
  },
  {
    "actual": 90.0,
    "prediction_A": 116.0,
    "prediction_B": 55.0
  },
  {
    "actual": 77.0,
    "prediction_A": 90.0,
    "prediction_B": 73.67
  },
  {
    "actual": 36.0,
    "prediction_A": 77.0,
    "prediction_B": 94.33
  },
  {
    "actual": 46.0,
    "prediction_A": 36.0,
    "prediction_B": 67.67
  },
  {
    "actual": 13.0,
    "prediction_A": 46.0,
    "prediction_B": 53.0
  },
  {
    "actual": 90.0,
    "prediction_A": 13.0,
    "prediction_B": 31.67
  },
  {
    "actual": 14.0,
    "prediction_A": 90.0,
    "prediction_B": 49.67
  },
  {
    "actual": 68.0,
    "prediction_A": 14.0,
    "prediction_B": 39.0
  },
  {
    "actual": 74.0,
    "prediction_A": 68.0,
    "prediction_B": 57.33
  },
  {
    "actual": 98.0,
    "prediction_A": 74.0,
    "prediction_B": 52.0
  },
  {
    "actual": 11.0,
    "prediction_A": 98.0,
    "prediction_B": 80.0
  },
  {
    "actual": 192.0,
    "prediction_A": 11.0,
    "prediction_B": 61.0
  },
  {
    "actual": 158.0,
    "prediction_A": 192.0,
    "prediction_B": 100.33
  },
  {
    "actual": 23.0,
    "prediction_A": 158.0,
    "prediction_B": 120.33
  }
]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>", "model_a_mae": "<number>", "model_b_mae": "<number>", "selected_model": "<string>"}}`
Do not include calculations outside the JSON object.
