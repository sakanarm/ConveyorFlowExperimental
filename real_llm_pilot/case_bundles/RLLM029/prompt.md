# Beijing public-data microtask RLLM029

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `eda` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Gucheng",
    "pm25": 107.0,
    "temperature": 13.2,
    "wind_speed": 0.0
  },
  {
    "station": "Gucheng",
    "pm25": 63.0,
    "temperature": 27.1,
    "wind_speed": 0.7
  },
  {
    "station": "Gucheng",
    "pm25": 12.0,
    "temperature": 5.4,
    "wind_speed": 0.6
  },
  {
    "station": "Gucheng",
    "pm25": 260.0,
    "temperature": 4.2,
    "wind_speed": 1.2
  },
  {
    "station": "Gucheng",
    "pm25": 76.0,
    "temperature": 22.4,
    "wind_speed": 0.6
  },
  {
    "station": "Gucheng",
    "pm25": 68.0,
    "temperature": 24.7,
    "wind_speed": 0.8
  },
  {
    "station": "Gucheng",
    "pm25": 240.0,
    "temperature": -0.5,
    "wind_speed": 0.6
  },
  {
    "station": "Gucheng",
    "pm25": 29.0,
    "temperature": 7.3,
    "wind_speed": 0.5
  },
  {
    "station": "Gucheng",
    "pm25": 136.0,
    "temperature": 28.6,
    "wind_speed": 1.4
  },
  {
    "station": "Gucheng",
    "pm25": 59.0,
    "temperature": 17.0,
    "wind_speed": 0.6
  },
  {
    "station": "Gucheng",
    "pm25": 9.0,
    "temperature": -5.2,
    "wind_speed": 1.9
  },
  {
    "station": "Gucheng",
    "pm25": 74.0,
    "temperature": 19.7,
    "wind_speed": 3.3
  },
  {
    "station": "Gucheng",
    "pm25": 45.0,
    "temperature": 24.2,
    "wind_speed": 1.2
  },
  {
    "station": "Gucheng",
    "pm25": 46.0,
    "temperature": 24.0,
    "wind_speed": 1.0
  },
  {
    "station": "Gucheng",
    "pm25": 25.0,
    "temperature": 6.9,
    "wind_speed": 0.5
  },
  {
    "station": "Gucheng",
    "pm25": 107.0,
    "temperature": 0.1,
    "wind_speed": 0.7
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
