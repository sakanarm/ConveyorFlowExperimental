# Beijing public-data microtask RLLM028

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `validate_load` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Dingling",
    "pm25": 111.0,
    "temperature": 25.8,
    "wind_speed": 2.0
  },
  {
    "station": "Dingling",
    "pm25": 72.0,
    "temperature": 29.5,
    "wind_speed": 1.6
  },
  {
    "station": "Dingling",
    "pm25": 5.0,
    "temperature": 9.9,
    "wind_speed": 3.0
  },
  {
    "station": "Dingling",
    "pm25": 320.0,
    "temperature": 4.4,
    "wind_speed": 1.6
  },
  {
    "station": "Dingling",
    "pm25": 74.0,
    "temperature": 29.1,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 136.0,
    "temperature": 23.1,
    "wind_speed": 2.4
  },
  {
    "station": "Dingling",
    "pm25": 14.0,
    "temperature": 4.0,
    "wind_speed": 4.7
  },
  {
    "station": "Dingling",
    "pm25": 62.0,
    "temperature": 3.6,
    "wind_speed": 0.8
  },
  {
    "station": "Dingling",
    "pm25": 216.0,
    "temperature": 25.2,
    "wind_speed": 1.1
  },
  {
    "station": "Dingling",
    "pm25": 225.0,
    "temperature": 26.2,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 41.0,
    "temperature": 16.5,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 226.0,
    "temperature": 2.4,
    "wind_speed": 1.1
  },
  {
    "station": "Dingling",
    "pm25": 8.0,
    "temperature": 20.4,
    "wind_speed": 6.7
  },
  {
    "station": "Dingling",
    "pm25": 36.0,
    "temperature": 29.5,
    "wind_speed": 2.6
  },
  {
    "station": "Dingling",
    "pm25": 5.0,
    "temperature": 11.23,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 8.0,
    "temperature": -2.7,
    "wind_speed": 1.9
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
