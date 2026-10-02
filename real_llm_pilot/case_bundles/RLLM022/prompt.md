# Beijing public-data microtask RLLM022

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D1.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Dingling",
    "pm25": 50.0,
    "temperature": 25.4,
    "wind_speed": 2.8
  },
  {
    "station": "Dingling",
    "pm25": 39.0,
    "temperature": 26.1,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 123.0,
    "temperature": 1.0,
    "wind_speed": 0.6
  },
  {
    "station": "Dingling",
    "pm25": 74.0,
    "temperature": 30.5,
    "wind_speed": 2.0
  },
  {
    "station": "Dingling",
    "pm25": 316.0,
    "temperature": 11.6,
    "wind_speed": 0.5
  },
  {
    "station": "Dingling",
    "pm25": 221.0,
    "temperature": -0.9,
    "wind_speed": 1.2
  },
  {
    "station": "Dingling",
    "pm25": 37.0,
    "temperature": 20.8,
    "wind_speed": 2.5
  },
  {
    "station": "Dingling",
    "pm25": 49.0,
    "temperature": -4.6,
    "wind_speed": 1.1
  },
  {
    "station": "Dingling",
    "pm25": 43.0,
    "temperature": -4.6,
    "wind_speed": 1.6
  },
  {
    "station": "Dingling",
    "pm25": 64.0,
    "temperature": 8.1,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 16.0,
    "temperature": 27.6,
    "wind_speed": 1.5
  },
  {
    "station": "Dingling",
    "pm25": 275.0,
    "temperature": -1.3,
    "wind_speed": 1.3
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
