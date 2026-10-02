# Beijing public-data microtask RLLM023

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D1.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Guanyuan",
    "pm25": 153.0,
    "temperature": 4.7,
    "wind_speed": 1.3
  },
  {
    "station": "Guanyuan",
    "pm25": 74.0,
    "temperature": 26.0,
    "wind_speed": 1.0
  },
  {
    "station": "Guanyuan",
    "pm25": 67.0,
    "temperature": -4.2,
    "wind_speed": 1.3
  },
  {
    "station": "Guanyuan",
    "pm25": 204.0,
    "temperature": 23.1,
    "wind_speed": 1.8
  },
  {
    "station": "Guanyuan",
    "pm25": 190.0,
    "temperature": 23.2,
    "wind_speed": 3.9
  },
  {
    "station": "Guanyuan",
    "pm25": 41.0,
    "temperature": 19.4,
    "wind_speed": 0.1
  },
  {
    "station": "Guanyuan",
    "pm25": 9.0,
    "temperature": -1.0,
    "wind_speed": 3.0
  },
  {
    "station": "Guanyuan",
    "pm25": 12.0,
    "temperature": 23.0,
    "wind_speed": 2.0
  },
  {
    "station": "Guanyuan",
    "pm25": 56.0,
    "temperature": 20.7,
    "wind_speed": 0.8
  },
  {
    "station": "Guanyuan",
    "pm25": 11.0,
    "temperature": -6.0,
    "wind_speed": 0.9
  },
  {
    "station": "Guanyuan",
    "pm25": 23.0,
    "temperature": 23.7,
    "wind_speed": 1.6
  },
  {
    "station": "Guanyuan",
    "pm25": 36.0,
    "temperature": 9.8,
    "wind_speed": 3.6
  }
]
```
Forecast rows:
```json
[]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>"}}`
Do not include calculations outside the JSON object.
