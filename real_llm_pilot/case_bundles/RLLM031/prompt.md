# Beijing public-data microtask RLLM031

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `validate_load` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Wanliu",
    "pm25": 12.0,
    "temperature": 9.5,
    "wind_speed": 3.9
  },
  {
    "station": "Wanliu",
    "pm25": 29.0,
    "temperature": 35.3,
    "wind_speed": 1.0
  },
  {
    "station": "Wanliu",
    "pm25": 53.0,
    "temperature": 19.4,
    "wind_speed": 1.3
  },
  {
    "station": "Wanliu",
    "pm25": 18.0,
    "temperature": 1.5,
    "wind_speed": 2.5
  },
  {
    "station": "Wanliu",
    "pm25": 90.0,
    "temperature": 9.9,
    "wind_speed": 1.6
  },
  {
    "station": "Wanliu",
    "pm25": 51.0,
    "temperature": 28.9,
    "wind_speed": 2.7
  },
  {
    "station": "Wanliu",
    "pm25": 166.0,
    "temperature": 11.0,
    "wind_speed": 0.0
  },
  {
    "station": "Wanliu",
    "pm25": 40.0,
    "temperature": 6.0,
    "wind_speed": 2.3
  },
  {
    "station": "Wanliu",
    "pm25": 22.0,
    "temperature": 22.5,
    "wind_speed": 2.1
  },
  {
    "station": "Wanliu",
    "pm25": 12.0,
    "temperature": 19.7,
    "wind_speed": 0.7
  },
  {
    "station": "Wanliu",
    "pm25": 121.0,
    "temperature": -5.6,
    "wind_speed": 1.2
  },
  {
    "station": "Wanliu",
    "pm25": 219.0,
    "temperature": 4.6,
    "wind_speed": 1.4
  },
  {
    "station": "Wanliu",
    "pm25": 141.0,
    "temperature": 24.0,
    "wind_speed": 0.6
  },
  {
    "station": "Wanliu",
    "pm25": 135.0,
    "temperature": 21.6,
    "wind_speed": 0.0
  },
  {
    "station": "Wanliu",
    "pm25": 38.0,
    "temperature": 23.18,
    "wind_speed": 1.2
  },
  {
    "station": "Wanliu",
    "pm25": 376.0,
    "temperature": -0.6,
    "wind_speed": 1.3
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
