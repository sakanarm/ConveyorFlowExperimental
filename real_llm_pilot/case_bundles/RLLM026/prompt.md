# Beijing public-data microtask RLLM026

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D1.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Wanshouxigong",
    "pm25": 21.0,
    "temperature": 26.7,
    "wind_speed": 2.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 16.0,
    "temperature": 17.0,
    "wind_speed": 2.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 41.0,
    "temperature": 18.0,
    "wind_speed": 2.0
  },
  {
    "station": "Wanshouxigong",
    "pm25": 83.0,
    "temperature": 4.7,
    "wind_speed": 1.8
  },
  {
    "station": "Wanshouxigong",
    "pm25": 69.0,
    "temperature": 23.9,
    "wind_speed": 0.5
  },
  {
    "station": "Wanshouxigong",
    "pm25": 27.0,
    "temperature": -0.5,
    "wind_speed": 0.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 10.0,
    "temperature": 7.4,
    "wind_speed": 4.3
  },
  {
    "station": "Wanshouxigong",
    "pm25": 159.0,
    "temperature": 25.1,
    "wind_speed": 0.8
  },
  {
    "station": "Wanshouxigong",
    "pm25": 14.0,
    "temperature": 2.6,
    "wind_speed": 5.2
  },
  {
    "station": "Wanshouxigong",
    "pm25": 65.0,
    "temperature": 14.5,
    "wind_speed": 1.1
  },
  {
    "station": "Wanshouxigong",
    "pm25": 22.0,
    "temperature": 30.2,
    "wind_speed": 1.5
  },
  {
    "station": "Wanshouxigong",
    "pm25": 140.0,
    "temperature": -4.2,
    "wind_speed": 1.2
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
