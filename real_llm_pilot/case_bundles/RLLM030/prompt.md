# Beijing public-data microtask RLLM030

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `eda` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Shunyi",
    "pm25": 8.0,
    "temperature": 10.8,
    "wind_speed": 3.5
  },
  {
    "station": "Shunyi",
    "pm25": 53.0,
    "temperature": 26.7,
    "wind_speed": 2.2
  },
  {
    "station": "Shunyi",
    "pm25": 106.0,
    "temperature": 4.3,
    "wind_speed": 0.9
  },
  {
    "station": "Shunyi",
    "pm25": 20.0,
    "temperature": 5.1,
    "wind_speed": 2.3
  },
  {
    "station": "Shunyi",
    "pm25": 97.0,
    "temperature": 19.6,
    "wind_speed": 1.7
  },
  {
    "station": "Shunyi",
    "pm25": 29.0,
    "temperature": 23.5,
    "wind_speed": 0.8
  },
  {
    "station": "Shunyi",
    "pm25": 3.0,
    "temperature": 6.1,
    "wind_speed": 2.5
  },
  {
    "station": "Shunyi",
    "pm25": 23.0,
    "temperature": 1.0,
    "wind_speed": 8.3
  },
  {
    "station": "Shunyi",
    "pm25": 50.0,
    "temperature": 28.1,
    "wind_speed": 3.0
  },
  {
    "station": "Shunyi",
    "pm25": 5.0,
    "temperature": 28.9,
    "wind_speed": 2.6
  },
  {
    "station": "Shunyi",
    "pm25": 307.0,
    "temperature": -0.2,
    "wind_speed": 1.1
  },
  {
    "station": "Shunyi",
    "pm25": 122.0,
    "temperature": 4.6,
    "wind_speed": 1.3
  },
  {
    "station": "Shunyi",
    "pm25": 134.0,
    "temperature": 28.5,
    "wind_speed": 1.8
  },
  {
    "station": "Shunyi",
    "pm25": 138.0,
    "temperature": 29.7,
    "wind_speed": 1.7
  },
  {
    "station": "Shunyi",
    "pm25": 52.0,
    "temperature": 19.2,
    "wind_speed": 2.6
  },
  {
    "station": "Shunyi",
    "pm25": 477.0,
    "temperature": -3.6,
    "wind_speed": 0.9
  }
]
```
Forecast rows:
```json
[]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>"}}`
Do not include calculations outside the JSON object.
