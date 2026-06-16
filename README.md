# CirclePy
Circle.so API made easy with async support for efficient Python integration.

## Headless client proxy

`HeadlessClient` accepts an optional proxy. Pass either a proxy URL string or a
`requests`-style proxies dictionary:

```python
from circlepy import HeadlessClient

client = HeadlessClient(
    api_key="your-api-key",
    email="member@example.com",
    proxy="http://127.0.0.1:8080",
)
```
