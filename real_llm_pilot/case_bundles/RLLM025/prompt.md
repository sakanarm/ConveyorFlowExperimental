# Beijing public-data microtask RLLM025

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D1.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Tiantan",
    "pm25": 83.0,
    "temperature": 30.5,
    "wind_speed": 1.6
  },
  {
    "station": "Tiantan",
    "pm25": 114.0,
    "temperature": 5.4,
    "wind_speed": 0.0
  },
  {
    "station": "Tiantan",
    "pm25": 213.0,
    "temperature": 2.3,
    "wind_speed": 1.3
  },
  {
    "station": "Tiantan",
    "pm25": 78.0,
    "temperature": 24.0,
    "wind_speed": 1.4
  },
  {
    "station": "Tiantan",
    "pm25": 216.0,
    "temperature": 7.0,
    "wind_speed": 1.9
  },
  {
    "station": "Tiantan",
    "pm25": 14.0,
    "temperature": 8.3,
    "wind_speed": 0.9
  },
  {
    "station": "Tiantan",
    "pm25": 40.0,
    "temperature": 25.0,
    "wind_speed": 3.9
  },
  {
    "station": "Tiantan",
    "pm25": 249.0,
    "temperature": 0.1,
    "wind_speed": 1.0
  },
  {
    "station": "Tiantan",
    "pm25": 29.0,
    "temperature": 16.0,
    "wind_speed": 4.3
  },
  {
    "station": "Tiantan",
    "pm25": 123.0,
    "temperature": 22.77,
    "wind_speed": 1.3
  },
  {
    "station": "Tiantan",
    "pm25": 30.0,
    "temperature": -3.1,
    "wind_speed": 1.0
  },
  {
    "station": "Tiantan",
    "pm25": 48.0,
    "temperature": -0.7,
    "wind_speed": 1.1
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
